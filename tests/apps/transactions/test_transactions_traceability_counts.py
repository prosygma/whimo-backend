from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.transactions.schemas.dto import TraceabilityCountsDTO

pytestmark = [pytest.mark.django_db]


class TestTransactionsTraceabilityCounts:
    URL = "transactions_traceability_counts"

    @pytest.mark.parametrize("traceability", TransactionTraceability)
    def test_producer(
        self,
        client: APIClient,
        traceability: TransactionTraceability,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(producer=True, buyer=user, traceability=traceability)

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[TraceabilityCountsDTO](**response_json)

        assert data_response.data.counts[traceability] == 1

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select transaction
        # 4. select transactions level 1 traceability counts
        # 5. select transactions level 2 ids
        assert len(queries) == 5, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_downstream(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        # seller3_1 -( full  )> seller2_1  |  seller2_1 -(conditional)> seller1_1 | seller1_1 -> user
        # seller3_2 -( full  )> seller2_1  |  seller2_2 -(incomplete)> seller1_1  |
        # seller3_3 -(partial)> seller2_2  |                                      |
        # ---
        # full = 2, conditional = 1, partial = 1, incomplete = 1

        seller3_1 = UserFactory.create()
        seller3_2 = UserFactory.create()
        seller3_3 = UserFactory.create()

        seller2_1 = UserFactory.create()
        seller2_2 = UserFactory.create()

        seller1_1 = UserFactory.create()

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_1,
            buyer=seller2_1,
            commodity=commodity,
            traceability=TransactionTraceability.FULL,
            status=TransactionStatus.ACCEPTED,
        )
        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_2,
            buyer=seller2_1,
            commodity=commodity,
            traceability=TransactionTraceability.FULL,
            status=TransactionStatus.ACCEPTED,
        )
        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_3,
            buyer=seller2_2,
            commodity=commodity,
            traceability=TransactionTraceability.PARTIAL,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller2_1,
            buyer=seller1_1,
            commodity=commodity,
            traceability=TransactionTraceability.CONDITIONAL,
            status=TransactionStatus.ACCEPTED,
        )
        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller2_2,
            buyer=seller1_1,
            commodity=commodity,
            traceability=TransactionTraceability.INCOMPLETE,
            status=TransactionStatus.ACCEPTED,
        )

        transaction = TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller1_1,
            buyer=user,
            commodity=commodity,
            traceability=None,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[TraceabilityCountsDTO](**response_json)

        assert data_response.data.counts[TransactionTraceability.FULL] == 2  # noqa: PLR2004
        assert data_response.data.counts[TransactionTraceability.CONDITIONAL] == 1
        assert data_response.data.counts[TransactionTraceability.PARTIAL] == 1
        assert data_response.data.counts[TransactionTraceability.INCOMPLETE] == 1

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select transaction
        # 4. select transactions level 1 traceability counts
        # 5. select transactions level 2 ids
        # 6. select transactions level 2 traceability counts
        # 7. select transactions level 3 ids
        # 8. select transactions level 3 traceability counts
        # 9. select transactions level 4 ids
        assert len(queries) == 9, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_transaction_does_not_exist(
        self,
        client: APIClient,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create()

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
