from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0012_historicaltransaction_is_automatic_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaluser",
            name="is_deleted",
            field=models.BooleanField(default=False, help_text="Indicates whether this user has been soft deleted"),
        ),
        migrations.AddField(
            model_name="user",
            name="is_deleted",
            field=models.BooleanField(default=False, help_text="Indicates whether this user has been soft deleted"),
        ),
    ]
