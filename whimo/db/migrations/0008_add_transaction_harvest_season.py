import django.db.models.deletion
from django.db import migrations, models

ACTIVE_STATUS = "active"

ADD_COVERAGE_CONSTRAINT = """
    ALTER TABLE transactions
    ADD CONSTRAINT transaction_harvest_season_covers_commodity
    FOREIGN KEY (harvest_season_id, commodity_id)
    REFERENCES harvest_season_commodities (harvest_season_id, commodity_id)
    DEFERRABLE INITIALLY DEFERRED
"""

DROP_COVERAGE_CONSTRAINT = """
    ALTER TABLE transactions
    DROP CONSTRAINT transaction_harvest_season_covers_commodity
"""


def stamp_harvest_seasons(apps, schema_editor) -> None:
    Transaction = apps.get_model("db", "Transaction")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")

    for season_commodity in HarvestSeasonCommodity.objects.all():
        start_date, end_date = season_commodity.period.lower, season_commodity.period.upper
        Transaction.objects.filter(
            commodity_id=season_commodity.commodity_id,
            created_at__date__gte=start_date,
            created_at__date__lt=end_date,
        ).update(harvest_season_id=season_commodity.harvest_season_id)

    for season_commodity in HarvestSeasonCommodity.objects.filter(status=ACTIVE_STATUS):
        Transaction.objects.filter(
            commodity_id=season_commodity.commodity_id,
            harvest_season__isnull=True,
        ).update(harvest_season_id=season_commodity.harvest_season_id)

    if Transaction.objects.filter(harvest_season__isnull=True).exists():
        raise RuntimeError("Every commodity holding transactions needs a harvest season before this migration.")


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0007_add_balance_harvest_season"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="harvest_season",
            field=models.ForeignKey(
                help_text="Harvest season this transaction belongs to",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="db.harvestseason",
            ),
        ),
        migrations.AddField(
            model_name="historicaltransaction",
            name="harvest_season",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Harvest season this transaction belongs to",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="db.harvestseason",
            ),
        ),
        migrations.RunPython(stamp_harvest_seasons, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="transaction",
            name="harvest_season",
            field=models.ForeignKey(
                help_text="Harvest season this transaction belongs to",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="db.harvestseason",
            ),
        ),
        migrations.RunSQL(sql=ADD_COVERAGE_CONSTRAINT, reverse_sql=DROP_COVERAGE_CONSTRAINT),
    ]
