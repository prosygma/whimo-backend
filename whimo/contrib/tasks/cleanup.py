import logging
from datetime import timedelta

from celery import current_app
from django.utils import timezone

from whimo.db.models import Gadget

logger = logging.getLogger(__name__)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def cleanup_unverified_gadgets() -> None:
    cutoff_date = timezone.now() - timedelta(days=30)
    unverified_gadgets = Gadget.objects.filter(is_verified=False, created_at__lte=cutoff_date)

    deleted_count, _ = unverified_gadgets.delete()
    logger.info("Cleaned up %d unverified gadgets older than 30 days", deleted_count)
