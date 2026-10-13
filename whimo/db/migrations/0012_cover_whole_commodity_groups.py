from collections import defaultdict

from django.db import migrations
from django.db.models import Count


def cover_whole_groups(apps, schema_editor) -> None:
    Commodity = apps.get_model("db", "Commodity")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")
    Transaction = apps.get_model("db", "Transaction")

    split_conversions = list(
        Transaction.objects.filter(type="conversion", group_id__isnull=False)
        .values("group_id")
        .annotate(seasons=Count("harvest_season_id", distinct=True))
        .filter(seasons__gt=1)
        .values_list("group_id", flat=True)[:20]
    )
    if split_conversions:
        raise RuntimeError(
            "Conversions span different harvest seasons: "
            + ", ".join(map(str, split_conversions))
            + ". Reconcile their season assignments before migrating."
        )

    coverage = defaultdict(dict)
    for item in HarvestSeasonCommodity.objects.select_related("commodity", "harvest_season"):
        coverage[item.commodity.group_id][item.harvest_season_id] = item.harvest_season

    for group_id, seasons in coverage.items():
        ordered = sorted(seasons.values(), key=lambda season: season.start_date)
        active = [season for season in ordered if season.status == "active"]
        overlaps = any(previous.end_date > current.start_date for previous, current in zip(ordered, ordered[1:]))
        if len(active) > 1 or overlaps:
            raise RuntimeError(
                f"Commodity group {group_id} has conflicting harvest seasons: "
                + ", ".join(str(season.pk) for season in ordered)
                + ". Configure one shared season for the whole group before migrating."
            )

    for group_id, seasons in coverage.items():
        for season in seasons.values():
            commodities = Commodity.objects.filter(group_id=group_id).exclude(
                harvest_season_commodities__harvest_season_id=season.pk,
            )
            HarvestSeasonCommodity.objects.bulk_create(
                HarvestSeasonCommodity(
                    harvest_season_id=season.pk,
                    commodity_id=commodity.pk,
                    period=(season.start_date, season.end_date),
                    status=season.status,
                )
                for commodity in commodities
            )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0011_retire_legacy_seasons"),
    ]

    operations = [
        migrations.RunPython(cover_whole_groups, migrations.RunPython.noop),
    ]
