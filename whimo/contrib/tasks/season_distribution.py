import logging
from datetime import datetime
from uuid import UUID

from celery import current_app
from django.db.models import Q

from whimo.db.models import Season, Transaction

logger = logging.getLogger(__name__)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def distribute_transactions_over_seasons(batch_size: int = 500) -> None:
    transactions_query = Transaction.objects.filter(season__isnull=True).order_by("pk")

    condition: dict[str, UUID] = {}
    while transactions := list(transactions_query.filter(**condition)[:batch_size]):
        if not transactions:
            break

        last_pk = transactions[-1].pk
        condition = {"pk__gt": last_pk}

        transactions_to_update = []
        for transaction in transactions:
            transaction.season = _find_matching_season(transaction.created_at, transaction.commodity_id)
            transactions_to_update.append(transaction)

        Transaction.objects.bulk_update(transactions_to_update, ["season", "updated_at"])


def _find_matching_season(created_at: datetime, commodity_id: UUID) -> Season | None:
    created_at_date = created_at.date()
    matching_seasons = (
        Season.objects.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=created_at_date),
            Q(end_date__isnull=True) | Q(end_date__gte=created_at_date),
            season_commodities__commodity_id=commodity_id,
        )
        .distinct()
        .order_by("start_date", "id")
    )

    return matching_seasons.first()
