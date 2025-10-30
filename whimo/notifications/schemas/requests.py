from datetime import datetime
from uuid import UUID

from pydantic import field_validator

from whimo.common.schemas.base import BaseRequest, PaginationRequest
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.notifications.schemas.dto import DeviceDTO, NotificationSettingsDTO
from whimo.notifications.schemas.errors import InvalidUpdateStatusError


class NotificationListRequest(PaginationRequest):
    search: str | None = None
    status: NotificationStatus | None = None
    types: list[NotificationType] | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    created_by_id: UUID | None = None


class NotificationStatusUpdateRequest(BaseRequest):
    status: NotificationStatus

    @field_validator("status", mode="before")
    def validate_status(cls, status: NotificationStatus) -> NotificationStatus:
        if status == NotificationStatus.READ:
            return status

        raise InvalidUpdateStatusError


class NotificationSettingsUpdateRequest(BaseRequest):
    settings: list[NotificationSettingsDTO]


class DeviceAddRequest(DeviceDTO, BaseRequest):
    pass
