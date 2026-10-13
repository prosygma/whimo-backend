from datetime import date

from django.db import migrations
from django.utils import timezone

# EFI's db/0006 and db/0009 seed harvest seasons that end on 2026-09-01, and db/0010
# refuses to run while a transaction falls outside every season. CamerTrace has been
# recording transactions since September 2026, so before db/0010 this rolls every
# elapsed active season forward one year, the way the nightly
# transition_harvest_seasons task does: the group's past season is archived, the
# active one becomes past and a new active season starts where it ended.


def next_year(day: date) -> date:
    return day.replace(year=day.year + 1)


def roll_forward(apps, schema_editor) -> None:
    HarvestSeason = apps.get_model("db", "HarvestSeason")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")
    today = timezone.now().date()

    while elapsed := list(HarvestSeason.objects.filter(status="active", end_date__lte=today)):
        for season in elapsed:
            commodity_ids = list(season.harvest_season_commodities.values_list("commodity_id", flat=True))

            previous_past = HarvestSeason.objects.filter(
                status="past", harvest_season_commodities__commodity_id__in=commodity_ids
            ).distinct()
            HarvestSeasonCommodity.objects.filter(harvest_season__in=previous_past).update(status="archived")
            previous_past.update(status="archived")

            season.status = "past"
            season.save(update_fields=["status"])
            season.harvest_season_commodities.update(status="past")

            start_date, end_date = season.end_date, next_year(season.end_date)
            label = f"{start_date.year}/{str(end_date.year)[2:]}"
            previous_label = f"{season.start_date.year}/{str(season.end_date.year)[2:]}"
            name = season.name.replace(previous_label, label)
            next_season = HarvestSeason.objects.create(
                name=name if name != season.name else f"{season.name} {label}",
                start_date=start_date,
                end_date=end_date,
                status="active",
            )
            HarvestSeasonCommodity.objects.bulk_create(
                HarvestSeasonCommodity(
                    harvest_season=next_season,
                    commodity_id=commodity_id,
                    period=(start_date, end_date),
                    status="active",
                )
                for commodity_id in commodity_ids
            )


class Migration(migrations.Migration):
    dependencies = [
        ("camertrace", "0001_languages_fr_en"),
        ("db", "0009_seed_harvest_seasons_per_group"),
    ]
    run_before = [
        ("db", "0010_stamp_chains_with_harvest_season"),
    ]

    operations = [
        migrations.RunPython(roll_forward, migrations.RunPython.noop),
    ]
