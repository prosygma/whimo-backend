from dataclasses import dataclass
from uuid import UUID

from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification, Transaction
from whimo.notifications.schemas.dto import NotificationDTO
from whimo.transactions.mappers import TransactionsMapper
from whimo.users.mappers.users import UsersMapper


@dataclass(slots=True)
class NotificationsMapper:
    @staticmethod
    def to_dto(notification: Notification) -> NotificationDTO:
        received_by = UsersMapper.to_dto(notification.received_by) if notification.received_by else None
        created_by = UsersMapper.to_dto(notification.created_by) if notification.created_by else None

        return NotificationDTO(
            id=notification.id,
            created_at=notification.created_at,
            data=notification.data,
            # ---
            status=NotificationStatus(notification.status),
            type=NotificationType(notification.type),
            # ---
            received_by=received_by,
            created_by=created_by,
        )

    @staticmethod
    def to_dto_list(notifications: list[Notification]) -> list[NotificationDTO]:
        return [NotificationsMapper.to_dto(notification) for notification in notifications]

    @staticmethod
    def from_transaction(
        notification_type: NotificationType,
        transaction: Transaction,
        received_by_id: UUID,
        created_by_id: UUID | None = None,
    ) -> Notification:
        transaction_dto = TransactionsMapper.to_dto(transaction, received_by_id, with_gadgets=False)

        data = {
            "transaction": transaction_dto.model_dump(mode="json"),
        }

        return Notification(
            data=data,
            # ---
            status=NotificationStatus.PENDING,
            type=notification_type,
            # ---
            received_by_id=received_by_id,
            created_by_id=created_by_id,
        )
