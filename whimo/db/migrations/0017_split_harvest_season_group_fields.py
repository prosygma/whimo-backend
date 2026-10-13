import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

HARVEST_SEASON_NAME_HELP_TEXT = (
    "Name of the harvest season shown to users, computed from commodity group, year and duration"
)


def backfill_harvest_season_fields(apps, schema_editor) -> None:
    HarvestSeason = apps.get_model("db", "HarvestSeason")
    HistoricalHarvestSeason = apps.get_model("db", "HistoricalHarvestSeason")

    for season in HarvestSeason.objects.prefetch_related("harvest_season_commodities__commodity"):
        group_ids = {item.commodity.group_id for item in season.harvest_season_commodities.all() if item.commodity_id}
        if len(group_ids) != 1:
            raise RuntimeError(
                f"Harvest season {season.pk} covers {len(group_ids)} commodity groups, expected exactly one. "
                "Reconcile its commodity coverage before migrating.",
            )

        span = (season.end_date.year - season.start_date.year) * 12 + (season.end_date.month - season.start_date.month)
        if span not in (6, 12):
            raise RuntimeError(
                f"Harvest season {season.pk} spans {span} months, expected 6 or 12. "
                "Reconcile its start/end dates before migrating.",
            )

        fields = {
            "commodity_group_id": group_ids.pop(),
            "year": season.start_date.year,
            "start_month": season.start_date.month,
            "duration_months": span,
            "country": "",
        }
        HarvestSeason.objects.filter(pk=season.pk).update(**fields)
        # History rows predate these fields; every snapshot of a season gets the same, current values.
        HistoricalHarvestSeason.objects.filter(id=season.pk).update(**fields)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0016_group_legacy_conversions"),
    ]

    operations = [
        migrations.AddField(
            model_name="harvestseason",
            name="country",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Country this season applies to, for admin search and filtering only",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="harvestseason",
            name="commodity_group",
            field=models.ForeignKey(
                help_text="Commodity group this season covers",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="harvest_seasons",
                to="db.commoditygroup",
            ),
        ),
        migrations.AddField(
            model_name="harvestseason",
            name="year",
            field=models.PositiveSmallIntegerField(
                help_text="Marketing year the season starts in",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="harvestseason",
            name="start_month",
            field=models.PositiveSmallIntegerField(
                help_text="Calendar month the season starts in",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
        migrations.AddField(
            model_name="harvestseason",
            name="duration_months",
            field=models.PositiveSmallIntegerField(
                choices=[(12, "1 year"), (6, "6 months")],
                default=12,
                help_text="Length of the season",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="harvestseason",
            name="name",
            field=models.CharField(help_text=HARVEST_SEASON_NAME_HELP_TEXT, max_length=255),
        ),
        migrations.AddField(
            model_name="historicalharvestseason",
            name="country",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Country this season applies to, for admin search and filtering only",
                max_length=100,
            ),
        ),
        migrations.AddField(
            model_name="historicalharvestseason",
            name="commodity_group",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Commodity group this season covers",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="db.commoditygroup",
            ),
        ),
        migrations.AddField(
            model_name="historicalharvestseason",
            name="year",
            field=models.PositiveSmallIntegerField(
                help_text="Marketing year the season starts in",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="historicalharvestseason",
            name="start_month",
            field=models.PositiveSmallIntegerField(
                help_text="Calendar month the season starts in",
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
        migrations.AddField(
            model_name="historicalharvestseason",
            name="duration_months",
            field=models.PositiveSmallIntegerField(
                choices=[(12, "1 year"), (6, "6 months")],
                default=12,
                help_text="Length of the season",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="historicalharvestseason",
            name="name",
            field=models.CharField(help_text=HARVEST_SEASON_NAME_HELP_TEXT, max_length=255),
        ),
        migrations.RunPython(backfill_harvest_season_fields, migrations.RunPython.noop),
        # Run the deferred foreign key checks queued by the data step now: PostgreSQL
        # refuses to ALTER a table that still has pending trigger events.
        migrations.RunSQL("SET CONSTRAINTS ALL IMMEDIATE", migrations.RunSQL.noop),
        migrations.AlterField(
            model_name="harvestseason",
            name="commodity_group",
            field=models.ForeignKey(
                help_text="Commodity group this season covers",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="harvest_seasons",
                to="db.commoditygroup",
            ),
        ),
        migrations.AlterField(
            model_name="harvestseason",
            name="year",
            field=models.PositiveSmallIntegerField(help_text="Marketing year the season starts in"),
        ),
        migrations.AlterField(
            model_name="harvestseason",
            name="start_month",
            field=models.PositiveSmallIntegerField(
                help_text="Calendar month the season starts in",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="harvestseason",
            name="duration_months",
            field=models.PositiveSmallIntegerField(
                choices=[(12, "1 year"), (6, "6 months")],
                default=12,
                help_text="Length of the season",
            ),
        ),
        migrations.AlterField(
            model_name="historicalharvestseason",
            name="year",
            field=models.PositiveSmallIntegerField(help_text="Marketing year the season starts in"),
        ),
        migrations.AlterField(
            model_name="historicalharvestseason",
            name="start_month",
            field=models.PositiveSmallIntegerField(
                help_text="Calendar month the season starts in",
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(12),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="historicalharvestseason",
            name="duration_months",
            field=models.PositiveSmallIntegerField(
                choices=[(12, "1 year"), (6, "6 months")],
                default=12,
                help_text="Length of the season",
            ),
        ),
        migrations.AddConstraint(
            model_name="harvestseason",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("commodity_group",),
                name="harvest_season_group_single_active",
            ),
        ),
        migrations.AddConstraint(
            model_name="harvestseason",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "past")),
                fields=("commodity_group",),
                name="harvest_season_group_single_past",
            ),
        ),
    ]
