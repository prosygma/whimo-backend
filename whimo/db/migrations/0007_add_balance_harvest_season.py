import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count, Sum

ACTIVE_STATUS = "active"


def assign_harvest_seasons(apps, schema_editor) -> None:
    Balance = apps.get_model("db", "Balance")
    HarvestSeasonCommodity = apps.get_model("db", "HarvestSeasonCommodity")

    Balance.objects.filter(volume=0).delete()

    for season_commodity in HarvestSeasonCommodity.objects.filter(status=ACTIVE_STATUS):
        Balance.objects.filter(commodity_id=season_commodity.commodity_id).update(
            harvest_season_id=season_commodity.harvest_season_id,
        )

    if Balance.objects.filter(harvest_season__isnull=True).exists():
        raise RuntimeError("Every commodity holding a balance needs an active harvest season before this migration.")

    merge_duplicated_balances(Balance)


def merge_duplicated_balances(Balance) -> None:
    duplicates = (
        Balance.objects.values("user_id", "commodity_id", "harvest_season_id")
        .annotate(total=Sum("volume"), rows=Count("id"))
        .filter(rows__gt=1)
    )
    for duplicate in duplicates:
        balances = Balance.objects.filter(
            user_id=duplicate["user_id"],
            commodity_id=duplicate["commodity_id"],
            harvest_season_id=duplicate["harvest_season_id"],
        ).order_by("created_at")

        kept = balances.first()
        Balance.objects.filter(pk=kept.pk).update(volume=duplicate["total"])
        balances.exclude(pk=kept.pk).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0006_seed_cocoa_harvest_season"),
    ]

    operations = [
        migrations.AddField(
            model_name="balance",
            name="harvest_season",
            field=models.ForeignKey(
                help_text="Harvest season the volume was harvested in",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="db.harvestseason",
            ),
        ),
        migrations.AddField(
            model_name="historicalbalance",
            name="harvest_season",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="Harvest season the volume was harvested in",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="db.harvestseason",
            ),
        ),
        migrations.RunPython(assign_harvest_seasons, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="balance",
            name="harvest_season",
            field=models.ForeignKey(
                help_text="Harvest season the volume was harvested in",
                on_delete=django.db.models.deletion.PROTECT,
                to="db.harvestseason",
            ),
        ),
        migrations.AddConstraint(
            model_name="balance",
            constraint=models.UniqueConstraint(
                fields=("user", "commodity", "harvest_season"),
                name="balance_user_commodity_harvest_season_unique",
            ),
        ),
    ]
