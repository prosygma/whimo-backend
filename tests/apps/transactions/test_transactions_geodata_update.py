from http import HTTPStatus
from io import BufferedReader
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.notifications import NotificationFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, SMALL_BATCH_SIZE
from whimo.db.enums import TransactionLocation
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification
from whimo.notifications.services.notifications import NotificationsService

pytestmark = [pytest.mark.django_db]


class TestTransactionsGeodataUpdate:
    URL = "transactions_geodata_update"

    @pytest.mark.parametrize("location", [TransactionLocation.FILE, TransactionLocation.QR])
    def test_success(  # noqa: PLR0913 Too many arguments in function definition
        self,
        location: TransactionLocation,
        client: APIClient,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        NotificationFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            type=NotificationType.GEODATA_MISSING,
            status=NotificationStatus.PENDING,
            data={
                "transaction": {"id": str(transaction.id)},
            },
        )

        mock_default_storage.save.return_value = None

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "location": location,
            "location_file": geo_json_file,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.location == location

        mock_default_storage.save.assert_called_once()

        assert Notification.objects.filter(type=NotificationType.GEODATA_UPDATED).count() == SMALL_BATCH_SIZE

    @pytest.mark.parametrize("location", [TransactionLocation.MANUAL, TransactionLocation.GPS])
    def test_invalid_location_type(
        self,
        location: TransactionLocation,
        client: APIClient,
        geo_json_file: BufferedReader,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "location": location,
            "location_file": geo_json_file,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_transaction_does_not_exist(
        self,
        client: APIClient,
        geo_json_file: BufferedReader,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        request_data = {
            "location": TransactionLocation.FILE,
            "location_file": geo_json_file,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(
        self,
        client: APIClient,
        geo_json_file: BufferedReader,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create()

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "location": TransactionLocation.FILE,
            "location_file": geo_json_file,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_file_upload_error(
        self,
        client: APIClient,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        mock_default_storage.save.side_effect = Exception("Storage error")

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "location": TransactionLocation.FILE,
            "location_file": geo_json_file,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        # Act
        response = client.patch(path=url)
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
        response = client.patch(path=url)
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
        response = client.patch(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_geodata_updated_missing_created_by(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(seller=user)

        NotificationFactory.create(
            type=NotificationType.GEODATA_MISSING,
            received_by=user,
            created_by=None,
            data={"transaction": {"id": str(transaction.id)}},
        )

        # Act
        created_notifications = NotificationsService.create_geodata_updated(
            transaction=transaction, created_by_id=user.id
        )

        # Assert
        assert len(created_notifications) == 0

        updated_notifications = Notification.objects.filter(type=NotificationType.GEODATA_UPDATED)
        assert updated_notifications.count() == 0
