import logging
from collections import defaultdict
from uuid import UUID, uuid4

from django.db import migrations

logger = logging.getLogger(__name__)


def cluster_legacy_conversions(transactions: list[dict]) -> dict[tuple, list[dict]]:
    clusters = defaultdict(list)
    for transaction in transactions:
        clusters[(transaction["created_by_id"], transaction["created_at"].replace(microsecond=0))].append(transaction)

    return clusters


def is_one_conversion(cluster: list[dict]) -> bool:
    has_input = any(transaction["seller_id"] for transaction in cluster)
    has_output = any(transaction["buyer_id"] for transaction in cluster)
    seasons = {transaction["harvest_season_id"] for transaction in cluster}

    return has_input and has_output and len(seasons) == 1


def group_legacy_conversions(apps, schema_editor) -> None:
    Transaction = apps.get_model("db", "Transaction")

    transactions = list(
        Transaction.objects.filter(type="conversion", group_id__isnull=True).values(
            "id",
            "created_at",
            "created_by_id",
            "harvest_season_id",
            "seller_id",
            "buyer_id",
        )
    )

    ungrouped: list[UUID] = []
    for cluster in cluster_legacy_conversions(transactions).values():
        transaction_ids = [transaction["id"] for transaction in cluster]

        if not is_one_conversion(cluster):
            ungrouped.extend(transaction_ids)
            continue

        Transaction.objects.filter(id__in=transaction_ids).update(group_id=uuid4())

    if ungrouped:
        # A cluster that spans two harvest seasons cannot become one conversion:
        # grouping it would place one conversion in two seasons. Moving a side into
        # the other season moves balance volume with it, which needs a decision.
        logger.warning(
            "%s legacy conversion rows stay ungrouped: %s",
            len(ungrouped),
            ", ".join(sorted(str(transaction_id) for transaction_id in ungrouped)),
        )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0015_distinguish_commodity_names"),
    ]

    operations = [
        migrations.RunPython(group_legacy_conversions, migrations.RunPython.noop),
    ]
