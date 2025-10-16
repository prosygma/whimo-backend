import json
import logging

from celery import current_app
from django.core.serializers.json import DjangoJSONEncoder
from firebase_admin.messaging import Message
from push_notifications.apns_async import Alert
from push_notifications.models import APNSDevice, GCMDevice

from whimo.db.models import NotificationSettings
from whimo.notifications.schemas.dto import NotificationDTO

logger = logging.getLogger(__name__)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_gcm_push(notification_data: dict) -> None:
    notification = NotificationDTO(**notification_data)
    if not notification.received_by:
        return

    if not NotificationSettings.objects.filter(
        user_id=notification.received_by.id,
        type=notification.type,
        is_enabled=True,
    ).exists():
        return

    notification_json = json.dumps(notification_data, cls=DjangoJSONEncoder)
    message = Message(data={"data": notification_json})

    for device in GCMDevice.objects.filter(user_id=notification.received_by.id):
        device.send_message(message)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_apns_push(notification_data: dict) -> None:
    notification = NotificationDTO(**notification_data)
    if not notification.received_by:
        return

    if not NotificationSettings.objects.filter(
        user_id=notification.received_by.id,
        type=notification.type,
        is_enabled=True,
    ).exists():
        return

    notification_json = json.dumps(notification_data, cls=DjangoJSONEncoder)
    alert = Alert(body=notification_json)

    # TODO: Uncomment when IOS app is ready
    # from whimo.db.enums.notifications import NotificationStatus
    # from whimo.db.models import Notification
    # badge_count = Notification.objects.filter(
    #     received_by_id=notification.received_by.id,
    #     status=NotificationStatus.PENDING,
    # ).count()

    for device in APNSDevice.objects.filter(user_id=notification.received_by.id):
        device.send_message(alert, mutable_content=True)
        # TODO: Uncomment when IOS app is ready
        # device.send_message(alert, badge=badge_count, mutable_content=True)
