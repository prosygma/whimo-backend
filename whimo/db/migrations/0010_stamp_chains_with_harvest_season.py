from collections import defaultdict
from datetime import date
from uuid import UUID

from django.db import migrations

UPDATE_BATCH_SIZE = 1000
REPORTED_GAPS = 20


def find_chain_root(parents: dict[UUID, UUID], transaction_id: UUID) -> UUID:
    root = transaction_id
    while parents[root] != root:
        root = parents[root]

    while parents[transaction_id] != root:
        parents[transaction_id], transaction_id = root, parents[transaction_id]

    return root


def join_chains(parents: dict[UUID, UUID], left: UUID, right: UUID) -> None:
    left_root, right_root = find_chain_root(parents, left), find_chain_root(parents, right)
    if left_root != right_root:
        parents[right_root] = left_root


def group_into_chains(transactions: list[dict]) -> dict[UUID, list[dict]]:
    parents = {transaction["id"]: transaction["id"] for transaction in transactions}

    incoming = defaultdict(list)
    for transaction in transactions:
        if transaction["buyer_id"]:
            incoming[(transaction["buyer_id"], transaction["commodity_id"])].append(transaction)

    for transaction in transactions:
        if not transaction["seller_id"]:
            continue

        for previous in incoming.get((transaction["seller_id"], transaction["commodity_id"]), ()):
            if previous["created_at"] <= transaction["created_at"]:
                join_chains(parents, previous["id"], transaction["id"])

    conversions = defaultdict(list)
    for transaction in transactions:
        if transaction["group_id"]:
            conversions[transaction["group_id"]].append(transaction["id"])

    for conversion_ids in conversions.values():
        for other_id in conversion_ids[1:]:
            join_chains(parents, conversion_ids[0], other_id)

    chains = defaultdict(list)
    for transaction in transactions:
        chains[find_chain_root(parents, transaction["id"])].append(transaction)

    return chains


def find_season_at(coverage: list[dict], day: date) -> UUID | None:
    for season in coverage:
        if season["period"].lower <= day < season["period"].upper:
            return season["harvest_season_id"]

    return None


def stamp_chains(apps, schema_editor) -> None:
    Transaction = apps.get_model("db", "Transaction")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")

    transactions = list(
        Transaction.objects.values("id", "created_at", "commodity_id", "seller_id", "buyer_id", "group_id")
    )
    if not transactions:
        return

    coverage = defaultdict(list)
    for season_commodity in HarvestSeasonCommodity.objects.values("commodity_id", "harvest_season_id", "period"):
        coverage[season_commodity["commodity_id"]].append(season_commodity)

    stamps = defaultdict(list)
    gaps = set()

    for chain in group_into_chains(transactions).values():
        harvested_on = min(transaction["created_at"] for transaction in chain).date()

        for transaction in chain:
            harvest_season_id = find_season_at(coverage[transaction["commodity_id"]], harvested_on)
            if harvest_season_id is None:
                gaps.add((transaction["commodity_id"], harvested_on))
                continue

            stamps[harvest_season_id].append(transaction["id"])

    if gaps:
        reported = sorted(f"{commodity_id} on {day}" for commodity_id, day in gaps)
        raise RuntimeError(
            f"{len(gaps)} commodity dates are not covered by any harvest season: {', '.join(reported[:REPORTED_GAPS])}"
        )

    for harvest_season_id, transaction_ids in stamps.items():
        for offset in range(0, len(transaction_ids), UPDATE_BATCH_SIZE):
            batch = transaction_ids[offset : offset + UPDATE_BATCH_SIZE]
            Transaction.objects.filter(id__in=batch).update(harvest_season_id=harvest_season_id)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0009_seed_harvest_seasons_per_group"),
    ]

    operations = [
        migrations.RunPython(stamp_chains, migrations.RunPython.noop),
    ]
