from http import HTTPStatus

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.notifications import NotificationFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums.notifications import NotificationStatus

pytestmark = [pytest.mark.django_db]


class TestNotificationsStatusUpdate:
    URL = "notification_status_update"

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(received_by=user, status=NotificationStatus.PENDING)

        url = reverse(self.URL, args=(notification.id,))
        request_data = {
            "status": NotificationStatus.READ,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        notification.refresh_from_db()
        assert notification.status == NotificationStatus.READ

    def test_set_pending(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(received_by=user, status=NotificationStatus.READ)

        url = reverse(self.URL, args=(notification.id,))
        request_data = {
            "status": NotificationStatus.PENDING,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_notification_not_pending(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(received_by=user, status=NotificationStatus.READ)

        url = reverse(self.URL, args=(notification.id,))
        request_data = {
            "status": NotificationStatus.READ,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_notification_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        request_data = {
            "status": NotificationStatus.READ,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
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
        other_user = UserFactory.create()
        notification = NotificationFactory.create(received_by=other_user, status=NotificationStatus.PENDING)

        url = reverse(self.URL, args=(notification.id,))
        request_data = {
            "status": NotificationStatus.READ,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
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
