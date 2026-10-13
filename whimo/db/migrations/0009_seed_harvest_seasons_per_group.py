from datetime import date

from django.db import migrations

CURRENT_SEASON = (date(2025, 9, 1), date(2026, 9, 1), "2025/26", "active")
PREVIOUS_SEASON = (date(2024, 9, 1), date(2025, 9, 1), "2024/25", "past")


def seed_seasons(apps, schema_editor) -> None:
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    HarvestSeason = apps.get_model("db", "HarvestSeason")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")

    for group in CommodityGroup.objects.all():
        for start_date, end_date, label, status in (CURRENT_SEASON, PREVIOUS_SEASON):
            commodities = list(
                group.commodities.exclude(
                    harvest_season_commodities__period__overlap=(start_date, end_date),
                )
            )
            if not commodities:
                continue

            season, _ = HarvestSeason.objects.get_or_create(
                name=f"{group.name} {label}",
                defaults={"start_date": start_date, "end_date": end_date, "status": status},
            )
            HarvestSeasonCommodity.objects.bulk_create(
                HarvestSeasonCommodity(
                    harvest_season=season,
                    commodity=commodity,
                    period=(start_date, end_date),
                    status=season.status,
                )
                for commodity in commodities
            )


def delete_seeded_seasons(apps, schema_editor) -> None:
    CommodityGroup = apps.get_model("db", "CommodityGroup")
    HarvestSeason = apps.get_model("db", "HarvestSeason")

    names = [
        f"{group.name} {label}"
        for group in CommodityGroup.objects.all()
        for _, _, label, _ in (CURRENT_SEASON, PREVIOUS_SEASON)
    ]
    HarvestSeason.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0008_add_transaction_harvest_season"),
    ]

    operations = [
        migrations.RunPython(seed_seasons, delete_seeded_seasons),
    ]
