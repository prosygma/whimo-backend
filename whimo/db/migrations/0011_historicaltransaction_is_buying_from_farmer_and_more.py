from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0010_alter_historicaltransaction_traceability_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaltransaction",
            name="is_buying_from_farmer",
            field=models.BooleanField(
                default=False, help_text="Whether this transaction is buying from a farmer directly"
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="is_buying_from_farmer",
            field=models.BooleanField(
                default=False, help_text="Whether this transaction is buying from a farmer directly"
            ),
        ),
    ]
