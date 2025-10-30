from dataclasses import dataclass
from typing import cast
from uuid import UUID

from django.db.models import Q, QuerySet

from whimo.common.schemas.base import Pagination
from whimo.common.schemas.errors import NotFound
from whimo.common.utils import get_user_model, paginate_queryset
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification, Transaction
from whimo.notifications.mappers.notifications import NotificationsMapper
from whimo.notifications.schemas.requests import (
    NotificationListRequest,
    NotificationStatusUpdateRequest,
)

User = get_user_model()


@dataclass(slots=True)
class NotificationsService:
    @staticmethod
    def get(user_id: UUID, notification_id: UUID) -> Notification:
        try:
            return (
                Notification.objects.select_related("received_by", "created_by")
                .prefetch_related(
                    User.objects.generate_prefetch_gadgets("received_by__"),
                    User.objects.generate_prefetch_gadgets("created_by__"),
                )
                .filter(received_by_id=user_id, pk=notification_id)
                .get()
            )
        except Notification.DoesNotExist as err:
            raise NotFound(errors={"notification": [notification_id]}) from err

    @staticmethod
    def list_notifications(user_id: UUID, request: NotificationListRequest) -> tuple[list[Notification], Pagination]:
        queryset = (
            NotificationsService._filter_notifications(user_id, request)
            .prefetch_related(
                User.objects.generate_prefetch_gadgets("received_by__"),
                User.objects.generate_prefetch_gadgets("created_by__"),
            )
            .order_by("-created_at")
        )
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def create_from_transaction(
        notification_type: NotificationType,
        transaction: Transaction,
        received_by_id: UUID,
        created_by_id: UUID | None = None,
    ) -> Notification:
        if (notification_type == NotificationType.GEODATA_MISSING) and (
            notification := Notification.objects.filter(
                type=NotificationType.GEODATA_MISSING,
                status=NotificationStatus.PENDING,
                received_by_id=received_by_id,
                data__transaction__id=str(transaction.pk),
            ).first()
        ):
            return notification

        notification = NotificationsMapper.from_transaction(
            notification_type=notification_type,
            transaction=transaction,
            received_by_id=received_by_id,
            created_by_id=created_by_id,
        )

        notification.save()
        return notification

    @staticmethod
    def create_geodata_updated(transaction: Transaction, created_by_id: UUID) -> list[Notification]:
        notifications = Notification.objects.filter(
            type=NotificationType.GEODATA_MISSING,
            data__transaction__id=str(transaction.pk),
        )

        created_notifications = []
        for notification in notifications:
            if not notification.created_by_id:
                continue

            created_notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.GEODATA_UPDATED,
                transaction=transaction,
                received_by_id=notification.created_by_id,
                created_by_id=created_by_id,
            )
            created_notifications.append(created_notification)

        return created_notifications

    @staticmethod
    def update_status(user_id: UUID, notification_id: UUID, request: NotificationStatusUpdateRequest) -> None:
        try:
            notification = Notification.objects.get(
                pk=notification_id,
                received_by_id=user_id,
                status=NotificationStatus.PENDING,
            )
        except Notification.DoesNotExist as err:
            raise NotFound(errors={"notification": [notification_id]}) from err

        notification.status = request.status
        notification.save(update_fields=["updated_at", "status"])

    @staticmethod
    def _filter_notifications(user_id: UUID, request: NotificationListRequest) -> QuerySet[Notification]:
        queryset = Notification.objects.select_related("received_by", "created_by").filter(received_by_id=user_id)

        if search := request.search:
            queryset = queryset.filter(Q(type__icontains=search) | Q(data__icontains=search))

        if status := request.status:
            queryset = queryset.filter(status=status)

        if notification_types := request.types:
            queryset = queryset.filter(type__in=notification_types)

        if created_at_from := request.created_at_from:
            queryset = queryset.filter(created_at__gte=created_at_from)

        if created_at_to := request.created_at_to:
            queryset = queryset.filter(created_at__lte=created_at_to)

        if created_by_id := request.created_by_id:
            queryset = queryset.filter(created_by_id=created_by_id)

        return cast(QuerySet[Notification], queryset)
