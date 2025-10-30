import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0024_gadget_cleanup_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="commodity",
            name="name_variants",
            field=models.JSONField(blank=True, default=list, help_text="Alternative name variations and translations"),
        ),
        migrations.AddField(
            model_name="commoditygroup",
            name="name_variants",
            field=models.JSONField(blank=True, default=list, help_text="Alternative name variations and translations"),
        ),
        migrations.AddIndex(
            model_name="commodity",
            index=django.contrib.postgres.indexes.GinIndex(fields=["name_variants"], name="db_comm_name_vars_gin_idx"),
        ),
        migrations.AddIndex(
            model_name="commoditygroup",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["name_variants"], name="db_commgrp_name_vars_gin_idx"
            ),
        ),
    ]
