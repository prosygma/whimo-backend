from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.notifications import APNSDeviceFactory, GCMDeviceFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.notifications.schemas.dto import DeviceDTO

pytestmark = [pytest.mark.django_db]


class TestNotificationDevicesList:
    URL = reverse("notification_devices")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gcm_devices = GCMDeviceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)
        apns_devices = APNSDeviceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[list[DeviceDTO]](**response_json)
        devices_ids = {device.registration_id for device in gcm_devices + apns_devices}
        response_ids = {device.registration_id for device in data_response.data}
        assert devices_ids == response_ids

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select gcm devices
        # 4. select apns devices
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

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
