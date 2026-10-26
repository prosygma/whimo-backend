from django.db import migrations, models

COMMODITY_HELP_TEXT = "Archived commodities are hidden from new data entry"
COMMODITY_GROUP_HELP_TEXT = "Archived groups are hidden from new data entry"


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0018_register_harvest_season_lifecycle_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="commodity",
            name="is_archived",
            field=models.BooleanField(default=False, help_text=COMMODITY_HELP_TEXT),
        ),
        migrations.AddField(
            model_name="commoditygroup",
            name="is_archived",
            field=models.BooleanField(default=False, help_text=COMMODITY_GROUP_HELP_TEXT),
        ),
        migrations.AddField(
            model_name="historicalcommodity",
            name="is_archived",
            field=models.BooleanField(default=False, help_text=COMMODITY_HELP_TEXT),
        ),
        migrations.AddField(
            model_name="historicalcommoditygroup",
            name="is_archived",
            field=models.BooleanField(default=False, help_text=COMMODITY_GROUP_HELP_TEXT),
        ),
    ]
