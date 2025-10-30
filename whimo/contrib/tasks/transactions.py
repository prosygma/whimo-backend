import logging

from celery import current_app
from django.db import transaction as db_transaction
from django.utils import timezone

from whimo.db.enums import TransactionStatus
from whimo.db.enums.notifications import NotificationType
from whimo.db.models import Transaction
from whimo.notifications.services.notifications import NotificationsService

logger = logging.getLogger(__name__)


@current_app.task
def expire_transactions() -> None:
    from whimo.notifications.services.notifications_push import NotificationsPushService

    expired_transactions = Transaction.objects.filter(expires_at__lte=timezone.now())
    logger.info("Expiring %d transactions", expired_transactions.count())

    for transaction in expired_transactions:
        transaction.status = TransactionStatus.NO_RESPONSE
        transaction.expires_at = None

        with db_transaction.atomic():
            transaction.save(update_fields=["updated_at", "status", "expires_at"])
            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.TRANSACTION_EXPIRED,
                transaction=transaction,
                received_by_id=transaction.created_by_id,
                created_by_id=None,
            )
            NotificationsPushService.send_push([notification.id])
