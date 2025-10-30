import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaltransaction",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                default=None,
                help_text="User who created this transaction",
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="created_by",
            field=models.ForeignKey(
                default=None,
                help_text="User who created this transaction",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="created_transactions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
