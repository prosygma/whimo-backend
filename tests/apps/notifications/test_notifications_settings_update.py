from http import HTTPStatus

import factory
import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.notifications import NotificationSettingsFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from whimo.db.enums.notifications import NotificationType
from whimo.db.models import NotificationSettings

pytestmark = [pytest.mark.django_db]


class TestNotificationSettingsUpdate:
    URL = reverse("notification_settings")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_notification_settings=False)
        settings_to_disable = set(list(NotificationType)[:3])
        settings_to_enable = set(list(NotificationType)[3:])

        NotificationSettingsFactory.create_batch(
            size=len(settings_to_disable),
            user=user,
            type=factory.Iterator(settings_to_disable),
            is_enabled=True,
        )

        NotificationSettingsFactory.create_batch(
            size=len(settings_to_enable),
            user=user,
            type=factory.Iterator(settings_to_enable),
            is_enabled=False,
        )

        request_data = {
            "settings": [
                {
                    "type": notification_type.value,
                    "is_enabled": notification_type in settings_to_enable,
                }
                for notification_type in NotificationType
            ]
        }

        client.login(user)

        # Act
        response = client.put(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        assert all(
            setting.is_enabled
            for setting in NotificationSettings.objects.filter(user=user, type__in=settings_to_enable)
        )

        assert all(
            not setting.is_enabled
            for setting in NotificationSettings.objects.filter(user=user, type__in=settings_to_disable)
        )

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.put(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.put(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.put(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
