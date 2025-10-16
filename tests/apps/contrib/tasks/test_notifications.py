from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.utils import timezone

from tests.factories.users import UserFactory
from whimo.contrib.tasks.notifications import send_apns_push, send_gcm_push
from whimo.db.enums.notifications import NotificationStatus, NotificationType

pytestmark = [pytest.mark.django_db]


class TestNotificationTasks:
    def test_send_gcm_push_no_received_by(self) -> None:
        # Arrange
        notification_data: dict[str, Any] = {
            "id": str(uuid4()),
            "created_at": timezone.now().isoformat(),
            "type": NotificationType.GEODATA_MISSING.value,
            "status": NotificationStatus.PENDING.value,
            "received_by": None,
            "created_by": None,
            "data": {},
        }

        # Act
        result = send_gcm_push(notification_data)

        # Assert
        assert result is None

    @patch("whimo.contrib.tasks.notifications.GCMDevice")
    @patch("whimo.contrib.tasks.notifications.NotificationSettings")
    def test_send_gcm_push_no_settings(self, mock_settings: MagicMock, mock_gcm_device: MagicMock) -> None:
        # Arrange
        user = UserFactory.create()
        notification_data: dict[str, Any] = {
            "id": str(uuid4()),
            "created_at": timezone.now().isoformat(),
            "type": NotificationType.GEODATA_MISSING.value,
            "status": NotificationStatus.PENDING.value,
            "received_by": {"id": str(user.id), "username": user.username, "gadgets": []},
            "created_by": None,
            "data": {},
        }
        mock_settings.objects.filter.return_value.exists.return_value = False

        # Act
        result = send_gcm_push(notification_data)

        # Assert
        assert result is None
        mock_gcm_device.objects.filter.assert_not_called()

    def test_send_apns_push_no_received_by(self) -> None:
        # Arrange
        notification_data: dict[str, Any] = {
            "id": str(uuid4()),
            "created_at": timezone.now().isoformat(),
            "type": NotificationType.GEODATA_MISSING.value,
            "status": NotificationStatus.PENDING.value,
            "received_by": None,
            "created_by": None,
            "data": {},
        }

        # Act
        result = send_apns_push(notification_data)

        # Assert
        assert result is None

    @patch("whimo.contrib.tasks.notifications.APNSDevice")
    @patch("whimo.contrib.tasks.notifications.NotificationSettings")
    def test_send_apns_push_no_settings(self, mock_settings: MagicMock, mock_apns_device: MagicMock) -> None:
        # Arrange
        user = UserFactory.create()
        notification_data: dict[str, Any] = {
            "id": str(uuid4()),
            "created_at": timezone.now().isoformat(),
            "type": NotificationType.GEODATA_MISSING.value,
            "status": NotificationStatus.PENDING.value,
            "received_by": {"id": str(user.id), "username": user.username, "gadgets": []},
            "created_by": None,
            "data": {},
        }
        mock_settings.objects.filter.return_value.exists.return_value = False

        # Act
        result = send_apns_push(notification_data)

        # Assert
        assert result is None
        mock_apns_device.objects.filter.assert_not_called()

    # TODO: Uncomment when IOS app is ready
    # @patch("whimo.contrib.tasks.notifications.APNSDevice")
    # @patch("whimo.contrib.tasks.notifications.NotificationSettings")
    # @patch("whimo.contrib.tasks.notifications.Notification")
    # def test_send_apns_push_with_badge_count_zero(
    #     self, mock_notification: MagicMock, mock_settings: MagicMock, mock_apns_device: MagicMock
    # ) -> None:
    #     user = UserFactory.create()
    #     notification_data: dict[str, Any] = {
    #         "id": str(uuid4()),
    #         "created_at": timezone.now().isoformat(),
    #         "type": NotificationType.GEODATA_MISSING.value,
    #         "status": NotificationStatus.PENDING.value,
    #         "received_by": {"id": str(user.id), "username": user.username, "gadgets": []},
    #         "created_by": None,
    #         "data": {},
    #     }
    #     mock_settings.objects.filter.return_value.exists.return_value = True
    #     mock_notification.objects.filter.return_value.count.return_value = 0
    #     mock_device = MagicMock()
    #     mock_apns_device.objects.filter.return_value = [mock_device]
    #
    #     send_apns_push(notification_data)
    #
    #     mock_device.send_message.assert_called_once()
    #     call_kwargs = mock_device.send_message.call_args[1]
    #     assert call_kwargs["badge"] == 0
    #     assert call_kwargs["mutable_content"] is True
    #
    # @patch("whimo.contrib.tasks.notifications.APNSDevice")
    # @patch("whimo.contrib.tasks.notifications.NotificationSettings")
    # @patch("whimo.contrib.tasks.notifications.Notification")
    # def test_send_apns_push_with_badge_count_multiple(
    #     self, mock_notification: MagicMock, mock_settings: MagicMock, mock_apns_device: MagicMock
    # ) -> None:
    #     user = UserFactory.create()
    #     notification_data: dict[str, Any] = {
    #         "id": str(uuid4()),
    #         "created_at": timezone.now().isoformat(),
    #         "type": NotificationType.GEODATA_MISSING.value,
    #         "status": NotificationStatus.PENDING.value,
    #         "received_by": {"id": str(user.id), "username": user.username, "gadgets": []},
    #         "created_by": None,
    #         "data": {},
    #     }
    #     mock_settings.objects.filter.return_value.exists.return_value = True
    #     mock_notification.objects.filter.return_value.count.return_value = 5
    #     mock_device = MagicMock()
    #     mock_apns_device.objects.filter.return_value = [mock_device]
    #
    #     send_apns_push(notification_data)
    #
    #     mock_device.send_message.assert_called_once()
    #     call_kwargs = mock_device.send_message.call_args[1]
    #     assert call_kwargs["badge"] == 5
    #     assert call_kwargs["mutable_content"] is True
    #
    # @patch("whimo.contrib.tasks.notifications.APNSDevice")
    # @patch("whimo.contrib.tasks.notifications.NotificationSettings")
    # @patch("whimo.contrib.tasks.notifications.Notification")
    # def test_send_apns_push_badge_filters_by_user_and_pending_status(
    #     self, mock_notification: MagicMock, mock_settings: MagicMock, mock_apns_device: MagicMock
    # ) -> None:
    #     user = UserFactory.create()
    #     notification_data: dict[str, Any] = {
    #         "id": str(uuid4()),
    #         "created_at": timezone.now().isoformat(),
    #         "type": NotificationType.GEODATA_MISSING.value,
    #         "status": NotificationStatus.PENDING.value,
    #         "received_by": {"id": str(user.id), "username": user.username, "gadgets": []},
    #         "created_by": None,
    #         "data": {},
    #     }
    #     mock_settings.objects.filter.return_value.exists.return_value = True
    #     mock_notification.objects.filter.return_value.count.return_value = 3
    #     mock_device = MagicMock()
    #     mock_apns_device.objects.filter.return_value = [mock_device]
    #
    #     send_apns_push(notification_data)
    #
    #     mock_notification.objects.filter.assert_called_once_with(
    #         received_by_id=user.id, status=NotificationStatus.PENDING
    #     )
    #     mock_device.send_message.assert_called_once()
    #     call_kwargs = mock_device.send_message.call_args[1]
    #     assert call_kwargs["badge"] == 3
