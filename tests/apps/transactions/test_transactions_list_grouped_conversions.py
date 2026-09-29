from decimal import Decimal
from http import HTTPStatus
from uuid import UUID

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory, create_conversion
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.db.enums import TransactionAction, TransactionType
from whimo.transactions.schemas.dto import ConversionTransactionDTO, TransactionDTO

pytestmark = [pytest.mark.django_db]

ListResponse = PaginatedDataResponse[list[TransactionDTO | ConversionTransactionDTO]]


class TestTransactionsListGroupedConversions:
    URL = reverse("transactions_list")

    def test_conversion_is_one_item(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        purchase = TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)
        create_conversion(user, UUID(int=1), inputs=[Decimal(1000)], outputs=[Decimal(850), Decimal(150)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = ListResponse(**response_json)
        assert data_response.pagination.count == 2  # noqa: PLR2004 Magic value used in comparison

        transactions = [item for item in data_response.data if isinstance(item, TransactionDTO)]
        assert [transaction.id for transaction in transactions] == [purchase.id]

        conversion = next(item for item in data_response.data if isinstance(item, ConversionTransactionDTO))
        assert conversion.group_id == UUID(int=1)
        assert [item.volume for item in conversion.inputs] == [Decimal(-1000)]
        assert [item.volume for item in conversion.outputs] == [Decimal(850), Decimal(150)]

    def test_page_holds_whole_conversions(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        TransactionFactory.create_batch(size=2, type=TransactionType.DOWNSTREAM, buyer=user)
        for index in range(3):
            create_conversion(user, UUID(int=index + 1), inputs=[Decimal(10)], outputs=[Decimal(5), Decimal(3)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true&page_size=3")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        assert data_response.pagination.count == 5  # noqa: PLR2004 Magic value used in comparison
        assert data_response.pagination.total_pages == 2  # noqa: PLR2004 Magic value used in comparison
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison

        for item in data_response.data:
            if isinstance(item, ConversionTransactionDTO):
                assert len(item.inputs) == 1
                assert len(item.outputs) == 2  # noqa: PLR2004 Magic value used in comparison

    @pytest.mark.parametrize("matched_side", ["input", "output"])
    @pytest.mark.parametrize("lookup", ["search", "commodity_id", "commodity_group_id"])
    def test_filter_matches_any_row(self, matched_side: str, lookup: str, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        conversion_input, conversion_output = create_conversion(
            user,
            UUID(int=1),
            inputs=[Decimal(10)],
            outputs=[Decimal(5)],
        )
        create_conversion(user, UUID(int=2), inputs=[Decimal(10)], outputs=[Decimal(5)])

        commodity = (conversion_input if matched_side == "input" else conversion_output).commodity
        value = {
            "search": commodity.code,
            "commodity_id": commodity.id,
            "commodity_group_id": commodity.group_id,
        }[lookup]

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true&{lookup}={value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        assert len(data_response.data) == 1

        conversion = data_response.data[0]
        assert isinstance(conversion, ConversionTransactionDTO)
        assert conversion.group_id == UUID(int=1)
        assert [item.id for item in conversion.inputs] == [conversion_input.id]
        assert [item.id for item in conversion.outputs] == [conversion_output.id]

    def test_filter_by_harvest_season(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        conversion_input, _ = create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])
        create_conversion(user, UUID(int=2), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        # Act
        response = client.get(
            path=f"{self.URL}?group_conversions=true&harvest_season_id={conversion_input.harvest_season_id}",
        )
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        assert [getattr(item, "group_id", None) for item in data_response.data] == [UUID(int=1)]

    @pytest.mark.parametrize("transaction_type", TransactionType)
    def test_filter_by_type(self, transaction_type: TransactionType, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        TransactionFactory.create(producer=True, buyer=user)
        TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)
        create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true&type={transaction_type}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].type == transaction_type

    def test_filter_by_type_without_grouping(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)
        conversion = create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?type={TransactionType.CONVERSION}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert {transaction.id for transaction in data_response.data} == {row.id for row in conversion}

    @pytest.mark.parametrize("action", TransactionAction)
    def test_action_excludes_conversions(self, action: TransactionAction, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        purchase = TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)
        sale = TransactionFactory.create(type=TransactionType.DOWNSTREAM, seller=user)
        create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true&action={action}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        expected = purchase if action == TransactionAction.BUYING else sale
        assert [getattr(item, "id", None) for item in data_response.data] == [expected.id]

    def test_rows_stay_separate_without_grouping(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        conversion = create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5), Decimal(3)])

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert {transaction.id for transaction in data_response.data} == {row.id for row in conversion}
        assert {transaction.group_id for transaction in data_response.data} == {UUID(int=1)}

    def test_conversion_without_group_id_stays_separate(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        conversion = create_conversion(user, None, inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_conversions=true")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = ListResponse(**response_json)
        assert all(isinstance(item, TransactionDTO) for item in data_response.data)
        assert {getattr(item, "id", None) for item in data_response.data} == {row.id for row in conversion}

    def test_query_count_is_flat(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)
        create_conversion(user, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(user)

        with CaptureQueriesContext(connection) as single_queries:
            client.get(path=f"{self.URL}?group_conversions=true")

        for index in range(MEDIUM_BATCH_SIZE):
            create_conversion(user, UUID(int=index + 2), inputs=[Decimal(10)], outputs=[Decimal(5), Decimal(3)])

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=f"{self.URL}?group_conversions=true")

        # Assert
        assert response.status_code == HTTPStatus.OK, response.json()
        assert len(queries) == len(single_queries), queries_to_str(queries)
