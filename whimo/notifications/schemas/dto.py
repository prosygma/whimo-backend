from datetime import datetime

from pydantic import BaseModel

from whimo.common.schemas.dto import BaseModelDTO
from whimo.db.enums.notifications import NotificationDeviceType, NotificationStatus, NotificationType
from whimo.users.schemas.dto import UserDTO


class NotificationDTO(BaseModelDTO):
    created_at: datetime
    data: dict | None

    type: NotificationType
    status: NotificationStatus

    received_by: UserDTO | None
    created_by: UserDTO | None


class NotificationSettingsDTO(BaseModel):
    type: NotificationType
    is_enabled: bool


class DeviceDTO(BaseModel):
    type: NotificationDeviceType
    registration_id: str
