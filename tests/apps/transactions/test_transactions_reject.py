from http import HTTPStatus

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification

pytestmark = [pytest.mark.django_db]


class TestTransactionsReject:
    URL = "transactions_status_update"

    def test_success(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            created_by=seller,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.REJECTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.REJECTED

        notification = Notification.objects.get()

        assert notification.type == NotificationType.TRANSACTION_REJECTED
        assert notification.status == NotificationStatus.PENDING
        assert notification.data["transaction"]["id"] == str(transaction.pk)  # type: ignore
        assert notification.received_by_id == seller.id
        assert notification.created_by_id == user.id

    def test_transaction_does_not_exist(
        self,
        client: APIClient,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        request_data = {
            "status": TransactionStatus.REJECTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_pending(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.REJECTED,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.REJECTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
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
        transaction = TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.REJECTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_created_by_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            created_by=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.REJECTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.REJECTED

    @pytest.mark.parametrize("status", [TransactionStatus.PENDING, TransactionStatus.NO_RESPONSE])
    def test_invalid_status(
        self,
        status: TransactionStatus,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": status,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
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
