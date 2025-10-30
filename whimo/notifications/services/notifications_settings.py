from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from whimo.common.utils import get_user_model
from whimo.db.models import NotificationSettings
from whimo.notifications.schemas.requests import (
    NotificationSettingsUpdateRequest,
)

User = get_user_model()


@dataclass(slots=True)
class NotificationsSettingsService:
    @staticmethod
    def list_notification_settings(user_id: UUID) -> list[NotificationSettings]:
        return list(NotificationSettings.objects.filter(user_id=user_id).order_by("type"))

    @staticmethod
    def update_notification_settings(user_id: UUID, request: NotificationSettingsUpdateRequest) -> None:
        settings_to_enable = [setting.type for setting in request.settings if setting.is_enabled]
        settings_to_disable = [setting.type for setting in request.settings if not setting.is_enabled]

        with transaction.atomic():
            NotificationSettings.objects.filter(user_id=user_id, type__in=settings_to_enable).update(is_enabled=True)
            NotificationSettings.objects.filter(user_id=user_id, type__in=settings_to_disable).update(is_enabled=False)
