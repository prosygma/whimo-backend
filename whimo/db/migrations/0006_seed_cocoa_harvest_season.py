from datetime import date

from django.db import migrations

SEASON_LABEL = "2025/26"
SEASON_START = date(2025, 9, 1)
SEASON_END = date(2026, 9, 1)


def create_season(apps, schema_editor) -> None:
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    HarvestSeason = apps.get_model("db", "HarvestSeason")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")

    for group in CommodityGroup.objects.all():
        commodities = list(group.commodities.all())
        if not commodities:
            continue

        season = HarvestSeason.objects.create(
            name=f"{group.name} {SEASON_LABEL}",
            start_date=SEASON_START,
            end_date=SEASON_END,
            status="active",
        )
        HarvestSeasonCommodity.objects.bulk_create(
            HarvestSeasonCommodity(
                harvest_season=season,
                commodity=commodity,
                period=(SEASON_START, SEASON_END),
                status=season.status,
            )
            for commodity in commodities
        )


def delete_season(apps, schema_editor) -> None:
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    HarvestSeason = apps.get_model("db", "HarvestSeason")
    names = [f"{group.name} {SEASON_LABEL}" for group in CommodityGroup.objects.all()]
    HarvestSeason.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0005_create_harvest_seasons"),
    ]

    operations = [
        migrations.RunPython(create_season, delete_season),
    ]
