from dataclasses import dataclass
from uuid import UUID

from push_notifications.models import APNSDevice, GCMDevice

from whimo.common.utils import get_user_model
from whimo.contrib.tasks.notifications import send_apns_push, send_gcm_push
from whimo.db.enums.notifications import NotificationDeviceType, NotificationType
from whimo.db.models import Notification, NotificationSettings
from whimo.notifications.mappers.notifications import NotificationsMapper
from whimo.notifications.mappers.notifications_push import NotificationsPushMapper
from whimo.notifications.schemas.errors import DeviceAlreadyExistsError
from whimo.notifications.schemas.requests import DeviceAddRequest

User = get_user_model()


@dataclass(slots=True)
class NotificationsPushService:
    @staticmethod
    def list_devices(user_id: UUID) -> list[GCMDevice | APNSDevice]:
        gcm_devices = GCMDevice.objects.filter(user_id=user_id)
        apns_devices = APNSDevice.objects.filter(user_id=user_id)
        return list(gcm_devices) + list(apns_devices)

    @staticmethod
    def add_device(user_id: UUID, request: DeviceAddRequest) -> None:
        if (
            request.type == NotificationDeviceType.FCM
            and GCMDevice.objects.filter(registration_id=request.registration_id).exists()
        ) or (
            request.type == NotificationDeviceType.APNS
            and APNSDevice.objects.filter(registration_id=request.registration_id).exists()
        ):
            raise DeviceAlreadyExistsError

        device = NotificationsPushMapper.from_request(user_id, request)
        device.save()

    @staticmethod
    def send_push(notifications_ids: list[UUID]) -> None:
        if not notifications_ids:
            return

        notifications = list(
            Notification.objects.filter(id__in=notifications_ids).prefetch_related(
                User.objects.generate_prefetch_gadgets("received_by__"),
                User.objects.generate_prefetch_gadgets("created_by__"),
            )
        )
        if not notifications:
            return

        user_ids = {notification.received_by_id for notification in notifications}
        enabled_types = NotificationsPushService._get_enabled_types(notifications, user_ids)

        for notification in notifications:
            if (notification.received_by_id, notification.type) not in enabled_types:
                continue

            notification_data = NotificationsMapper.to_dto(notification).model_dump()
            send_gcm_push.delay(notification_data)
            send_apns_push.delay(notification_data)

    @staticmethod
    def _get_enabled_types(
        notifications: list[Notification], user_ids: set[UUID]
    ) -> set[tuple[UUID, NotificationType]]:
        notification_types = {notification.type for notification in notifications}
        settings = NotificationSettings.objects.filter(
            user_id__in=user_ids,
            type__in=notification_types,
            is_enabled=True,
        ).values_list("user_id", "type")
        return {(user_id, NotificationType(setting_type)) for user_id, setting_type in settings}
