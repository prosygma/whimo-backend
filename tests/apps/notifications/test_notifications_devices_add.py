from http import HTTPStatus

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from push_notifications.models import APNSDevice, GCMDevice
from syrupy import SnapshotAssertion

from tests.factories.notifications import APNSDeviceFactory, GCMDeviceFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums.notifications import NotificationDeviceType
from whimo.notifications.schemas.errors import DeviceAlreadyExistsError
from whimo.notifications.schemas.requests import DeviceAddRequest
from whimo.notifications.services.notifications_push import NotificationsPushService

pytestmark = [pytest.mark.django_db]


class TestNotificationDevicesAdd:
    URL = reverse("notification_devices")

    @pytest.mark.parametrize("device_type", NotificationDeviceType)
    def test_success(self, client: APIClient, device_type: NotificationDeviceType, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_notification_settings=False)

        request_data = {
            "type": str(device_type),
            "registration_id": "token",
        }
        sanitized_request = DeviceAddRequest.model_validate(request_data)

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        device: GCMDevice | APNSDevice
        if device_type == NotificationDeviceType.APNS:
            device = APNSDevice.objects.get(user=user)
        elif device_type == NotificationDeviceType.FCM:
            device = GCMDevice.objects.get(user=user)
        else:
            raise NotImplementedError

        assert device.registration_id == sanitized_request.registration_id

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.post(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.post(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.post(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_device_already_exists_error(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        GCMDeviceFactory.create(user=user, registration_id="existing_token")

        client.login(user)

        request_data = {"type": "FCM", "registration_id": "existing_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_device_already_exists_error_apns(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        APNSDeviceFactory.create(user=user, registration_id="existing_apns_token")

        client.login(user)

        request_data = {"type": "APNS", "registration_id": "existing_apns_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST


class TestNotificationsPushService:
    def test_add_device_fcm_conflict_direct(self) -> None:
        # Arrange
        user = UserFactory.create()
        GCMDeviceFactory.create(registration_id="conflict_token")
        request = DeviceAddRequest(type=NotificationDeviceType.FCM, registration_id="conflict_token")

        # Act & Assert
        with pytest.raises(DeviceAlreadyExistsError):
            NotificationsPushService.add_device(user.id, request)

    def test_add_device_apns_conflict_direct(self) -> None:
        # Arrange
        user = UserFactory.create()
        APNSDeviceFactory.create(registration_id="conflict_apns_token")
        request = DeviceAddRequest(type=NotificationDeviceType.APNS, registration_id="conflict_apns_token")

        # Act & Assert
        with pytest.raises(DeviceAlreadyExistsError):
            NotificationsPushService.add_device(user.id, request)
