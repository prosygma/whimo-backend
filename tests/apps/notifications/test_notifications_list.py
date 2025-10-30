import math
from datetime import timedelta
from http import HTTPStatus
from uuid import UUID, uuid4

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils.http import urlencode
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.notifications import NotificationFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.notifications.schemas.dto import NotificationDTO
from whimo.notifications.services.notifications_push import NotificationsPushService

pytestmark = [pytest.mark.django_db]


class TestNotificationsList:
    URL = reverse("notifications_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notifications = NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

        notification_ids = {notification.id for notification in notifications}
        response_notification_ids = {notification.id for notification in data_response.data}
        assert response_notification_ids == notification_ids

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        # 5. prefetch received_by gadgets
        # 6. prefetch created_by gadgets
        assert len(queries) == 6, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_type(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(received_by=user, type=NotificationType.TRANSACTION_PENDING)
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user, type=NotificationType.GEODATA_MISSING)

        search_term = "pending"

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == notification.id

    def test_search_by_data(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        notification = NotificationFactory.create(
            received_by=user, data={"transaction_id": "test-12345", "message": "New transaction"}
        )
        NotificationFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            received_by=user,
            data={"other": "data"},
        )

        search_term = "test-12345"

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == notification.id

    @pytest.mark.parametrize("status", NotificationStatus)
    def test_filter_by_status(
        self,
        status: NotificationStatus,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        NotificationFactory.create_batch(
            size=len(NotificationStatus),
            status=factory.Iterator(NotificationStatus),
            received_by=user,
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?status={status.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].status == status

    @pytest.mark.parametrize("notification_type", NotificationType)
    def test_filter_by_type(
        self,
        notification_type: NotificationType,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        NotificationFactory.create_batch(
            size=len(NotificationType),
            type=factory.Iterator(NotificationType),
            received_by=user,
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?types={notification_type.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].type == notification_type

    def test_filter_by_multiple_types(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        NotificationFactory.create_batch(
            size=len(NotificationType),
            type=factory.Iterator(NotificationType),
            received_by=user,
        )

        client.login(user)

        notification_types = [NotificationType.TRANSACTION_PENDING, NotificationType.GEODATA_MISSING]
        filters = {"types": [str(notification_type) for notification_type in notification_types]}
        query = urlencode(filters, doseq=True)

        # Act
        response = client.get(path=f"{self.URL}?{query}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == len(notification_types)

        response_types = {notification.type for notification in data_response.data}
        assert response_types == set(notification_types)

    def test_filter_by_created_at_from(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)

        created_at_from = (DEFAULT_DATETIME + timedelta(days=15)).strftime("%Y-%m-%d")
        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?created_at_from={created_at_from}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

    def test_filter_by_created_at_to(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)

        created_at_to = (DEFAULT_DATETIME + timedelta(days=15)).strftime("%Y-%m-%d")
        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?created_at_to={created_at_to}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

    def test_filter_by_created_by_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        creator = UserFactory.create()
        notification = NotificationFactory.create(received_by=user, created_by=creator)
        NotificationFactory.create_batch(size=SMALL_BATCH_SIZE, received_by=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?created_by_id={creator.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == notification.id

    @pytest.mark.parametrize(("page", "page_size"), [(1, 2), (2, 2)])
    def test_pagination(
        self,
        page: int,
        page_size: int,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        NotificationFactory.create_batch(size=MEDIUM_BATCH_SIZE, received_by=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert data_response.pagination.page == page
        assert data_response.pagination.page_size == page_size
        assert data_response.pagination.count == MEDIUM_BATCH_SIZE

        expected_total_pages = math.ceil(MEDIUM_BATCH_SIZE / page_size)
        assert data_response.pagination.total_pages == expected_total_pages

        remaining_items = max(0, MEDIUM_BATCH_SIZE - (page - 1) * page_size)
        expected_items_count = min(page_size, remaining_items)
        assert len(data_response.data) == expected_items_count

    def test_empty_result(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[NotificationDTO]](**response_json)
        assert len(data_response.data) == 0
        assert data_response.pagination.count == 0

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


class TestNotificationsPushService:
    def test_send_push_empty_notifications(self) -> None:
        # Arrange
        empty_notification_ids: list[UUID] = []

        # Act
        result = NotificationsPushService.send_push(empty_notification_ids)

        # Assert
        assert result is None

    def test_send_push_no_notifications_found(self) -> None:
        # Arrange
        nonexistent_notification_ids = [uuid4()]

        # Act
        result = NotificationsPushService.send_push(nonexistent_notification_ids)

        # Assert
        assert result is None

    def test_send_push_disabled_notification_type(
        self,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        receiver = UserFactory.create(with_notification_settings=False)

        notification = NotificationFactory.create(received_by=receiver, created_by=user)

        mock_gcm_delay = mocker.patch("whimo.contrib.tasks.notifications.send_gcm_push.delay")
        mock_apns_delay = mocker.patch("whimo.contrib.tasks.notifications.send_apns_push.delay")

        # Act
        NotificationsPushService.send_push([notification.id])

        # Assert
        mock_gcm_delay.assert_not_called()
        mock_apns_delay.assert_not_called()
