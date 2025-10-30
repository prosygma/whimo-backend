from dataclasses import dataclass

from whimo.db.enums.notifications import NotificationType
from whimo.db.models import NotificationSettings
from whimo.notifications.schemas.dto import NotificationSettingsDTO


@dataclass(slots=True)
class NotificationsSettingsMapper:
    @staticmethod
    def to_dto(settings: NotificationSettings) -> NotificationSettingsDTO:
        return NotificationSettingsDTO(
            type=NotificationType(settings.type),
            is_enabled=settings.is_enabled,
        )

    @staticmethod
    def to_dto_list(settings: list[NotificationSettings]) -> list[NotificationSettingsDTO]:
        return [NotificationsSettingsMapper.to_dto(setting) for setting in settings]
