from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0020_create_notifications_settings"),
    ]

    operations = [
        migrations.RenameField(
            model_name="historicaltransaction",
            old_name="latitude",
            new_name="transaction_latitude",
        ),
        migrations.RenameField(
            model_name="historicaltransaction",
            old_name="longitude",
            new_name="transaction_longitude",
        ),
        migrations.RenameField(
            model_name="transaction",
            old_name="latitude",
            new_name="transaction_latitude",
        ),
        migrations.RenameField(
            model_name="transaction",
            old_name="longitude",
            new_name="transaction_longitude",
        ),
    ]
