from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.db.enums.notifications import NotificationType
from whimo.notifications.schemas.dto import NotificationSettingsDTO

pytestmark = [pytest.mark.django_db]


class TestNotificationSettingsList:
    URL = reverse("notification_settings")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[list[NotificationSettingsDTO]](**response_json)
        notification_types = {notification_type.value for notification_type in NotificationType}
        response_types = {notification.type for notification in data_response.data}
        assert response_types == notification_types

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select settings
        assert len(queries) == 3, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
