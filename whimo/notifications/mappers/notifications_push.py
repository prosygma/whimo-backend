from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from push_notifications.models import APNSDevice, GCMDevice

from whimo.db.enums.notifications import NotificationDeviceType
from whimo.notifications.schemas.dto import DeviceDTO
from whimo.notifications.schemas.requests import DeviceAddRequest


@dataclass(slots=True)
class NotificationsPushMapper:
    @staticmethod
    def to_dto(device: GCMDevice | APNSDevice) -> DeviceDTO:
        if isinstance(device, APNSDevice):
            device_type = NotificationDeviceType.APNS
        elif isinstance(device, GCMDevice):
            device_type = NotificationDeviceType.FCM
        else:
            raise NotImplementedError  # pragma: no cover

        return DeviceDTO(
            type=device_type,
            registration_id=device.registration_id,
        )

    @staticmethod
    def to_dto_list(devices: list[GCMDevice | APNSDevice]) -> list[DeviceDTO]:
        return [NotificationsPushMapper.to_dto(device) for device in devices]

    @staticmethod
    def from_request(user_id: UUID, request: DeviceAddRequest) -> GCMDevice | APNSDevice:
        if request.type == NotificationDeviceType.FCM:
            return GCMDevice(
                user_id=user_id,
                registration_id=request.registration_id,
                application_id=settings.PUSH_NOTIFICATIONS_SETTINGS_FCM_APP_ID,
            )
        if request.type == NotificationDeviceType.APNS:
            return APNSDevice(
                user_id=user_id,
                registration_id=request.registration_id,
                application_id=settings.PUSH_NOTIFICATIONS_SETTINGS_APNS_APP_ID,
            )
        raise NotImplementedError  # pragma: no cover
