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
