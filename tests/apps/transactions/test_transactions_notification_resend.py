from http import HTTPStatus

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.notifications import (
    APNSDeviceFactory,
    GCMDeviceFactory,
    NotificationFactory,
    NotificationSettingsFactory,
)
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification

pytestmark = [pytest.mark.django_db]


class TestTransactionsNotificationResend:
    URL = "transactions_notification_resend"

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            type=TransactionType.DOWNSTREAM,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        notification = Notification.objects.get()

        assert notification.type == NotificationType.TRANSACTION_PENDING
        assert notification.status == NotificationStatus.PENDING
        assert notification.received_by_id == buyer.id
        assert notification.created_by_id == user.id
        assert notification.data["transaction"]["id"] == str(transaction.pk)  # type: ignore

    def test_multiple_notifications_created(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            type=TransactionType.DOWNSTREAM,
        )

        first_notification = NotificationFactory.create(
            type=NotificationType.TRANSACTION_PENDING,
            received_by=buyer,
            created_by=user,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        notifications = Notification.objects.filter(
            type=NotificationType.TRANSACTION_PENDING,
            received_by=buyer,
            created_by=user,
        )
        assert notifications.count() == 2  # noqa: PLR2004 Magic value used in comparison

        new_notification = notifications.exclude(id=first_notification.id).get()
        assert new_notification.status == NotificationStatus.PENDING
        assert new_notification.data["transaction"]["id"] == str(transaction.pk)  # type: ignore

    def test_transaction_not_pending(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.ACCEPTED,
            type=TransactionType.DOWNSTREAM,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

        assert Notification.objects.count() == 0

    def test_transaction_no_buyer(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            seller=user,
            buyer=None,
            status=TransactionStatus.PENDING,
            type=TransactionType.PRODUCER,
            created_by=user,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

        assert Notification.objects.count() == 0

    def test_transaction_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        client.login(user)

        # Act
        response = client.post(path=url)
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
        other_user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(
            seller=other_user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            type=TransactionType.DOWNSTREAM,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_user_is_buyer_not_seller(
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
            seller=seller,
            buyer=user,
            status=TransactionStatus.PENDING,
            type=TransactionType.DOWNSTREAM,
        )

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        # Act
        response = client.post(path=url)
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
        response = client.post(path=url)
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
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_push_notification_tasks(
        self,
        client: APIClient,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create(with_notification_settings=False)
        transaction = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            type=TransactionType.DOWNSTREAM,
        )

        NotificationSettingsFactory.create(
            user=buyer,
            type=NotificationType.TRANSACTION_PENDING,
            is_enabled=True,
        )

        GCMDeviceFactory.create(user=buyer)
        APNSDeviceFactory.create(user=buyer)

        mock_gcm_send = mocker.patch("push_notifications.models.GCMDevice.send_message")
        mock_apns_send = mocker.patch("push_notifications.models.APNSDevice.send_message")

        from typing import Any

        from whimo.contrib.tasks.notifications import send_apns_push, send_gcm_push

        def mock_gcm_delay(notification_data: dict[str, Any]) -> None:
            return send_gcm_push(notification_data)

        def mock_apns_delay(notification_data: dict[str, Any]) -> None:
            return send_apns_push(notification_data)

        mocker.patch("whimo.contrib.tasks.notifications.send_gcm_push.delay", side_effect=mock_gcm_delay)
        mocker.patch("whimo.contrib.tasks.notifications.send_apns_push.delay", side_effect=mock_apns_delay)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        mock_gcm_send.assert_called_once()
        mock_apns_send.assert_called_once()

        gcm_call_args = mock_gcm_send.call_args[0][0]
        apns_call_args = mock_apns_send.call_args[0][0]

        assert hasattr(gcm_call_args, "data")
        assert "data" in gcm_call_args.data

        assert hasattr(apns_call_args, "body")
