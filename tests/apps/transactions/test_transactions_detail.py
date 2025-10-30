from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.transactions.schemas.dto import TransactionDTO

pytestmark = [pytest.mark.django_db]


class TestTransactionsDetail:
    URL = "transactions_detail"

    def test_producer(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(producer=True, buyer=user)

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[TransactionDTO](**response_json)

        assert data_response.data.traceability == transaction.traceability
        assert data_response.data.type == transaction.type
        assert data_response.data.status == transaction.status
        assert data_response.data.volume == transaction.volume
        assert data_response.data.location == transaction.location
        assert data_response.data.transaction_latitude == transaction.transaction_latitude
        assert data_response.data.transaction_longitude == transaction.transaction_longitude

        assert data_response.data.commodity.id == transaction.commodity_id

        assert data_response.data.buyer
        assert data_response.data.buyer.id == transaction.buyer_id

        assert data_response.data.seller is None

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select transaction
        # 4. select buyer gadgets
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_downstream(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(type=TransactionType.DOWNSTREAM, buyer=user)

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[TransactionDTO](**response_json)

        assert data_response.data.traceability == transaction.traceability
        assert data_response.data.type == transaction.type
        assert data_response.data.status == transaction.status
        assert data_response.data.volume == transaction.volume
        assert data_response.data.location == transaction.location
        assert data_response.data.transaction_latitude == transaction.transaction_latitude
        assert data_response.data.transaction_longitude == transaction.transaction_longitude

        assert data_response.data.commodity.id == transaction.commodity_id

        assert data_response.data.buyer
        assert data_response.data.buyer.id == transaction.buyer_id

        assert data_response.data.seller
        assert data_response.data.seller.id == transaction.seller_id

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select transaction
        # 4. select buyer gadgets
        # 5. select seller gadgets
        assert len(queries) == 5, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_downstream_with_traceability(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        seller = UserFactory.create()
        user = UserFactory.create()

        TransactionFactory.create(
            buyer=seller,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.FULL,
        )

        TransactionFactory.create(
            buyer=seller,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.INCOMPLETE,
        )

        TransactionFactory.create(
            buyer=seller,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.CONDITIONAL,
        )

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
            traceability=None,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[TransactionDTO](**response_json)

        assert transaction.traceability is None
        assert data_response.data.traceability == TransactionTraceability.INCOMPLETE

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
