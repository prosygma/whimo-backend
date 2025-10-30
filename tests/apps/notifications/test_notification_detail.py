from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.notifications import NotificationFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.db.enums.notifications import NotificationType
from whimo.notifications.schemas.dto import NotificationDTO

pytestmark = [pytest.mark.django_db]


class TestNotificationDetail:
    URL = "notification_detail"

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(received_by=user)

        url = reverse(self.URL, args=(notification.id,))

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[NotificationDTO](**response_json)

        assert data_response.data.type == notification.type
        assert data_response.data.status == notification.status
        assert data_response.data.data == notification.data

        assert data_response.data.received_by
        assert data_response.data.received_by.id == notification.received_by_id

        assert data_response.data.created_by
        assert data_response.data.created_by.id == notification.created_by_id

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select notification
        # 4. select received_by gadgets
        # 5. select created_by gadgets
        assert len(queries) == 5, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_with_different_notification_types(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(
            received_by=user,
            type=NotificationType.TRANSACTION_PENDING,
            data={"transaction": {"id": "123", "status": "pending"}},
        )

        url = reverse(self.URL, args=(notification.id,))

        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[NotificationDTO](**response_json)

        assert data_response.data.type == NotificationType.TRANSACTION_PENDING
        assert data_response.data.data == {"transaction": {"id": "123", "status": "pending"}}

    def test_notification_does_not_exist(
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

    def test_notification_not_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create()

        url = reverse(self.URL, args=(notification.id,))

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
