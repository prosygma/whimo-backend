from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0013_historicaluser_is_deleted_user_is_deleted"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaltransaction",
            name="expires_at",
            field=models.DateTimeField(blank=True, help_text="When this transaction expires", null=True),
        ),
        migrations.AddField(
            model_name="transaction",
            name="expires_at",
            field=models.DateTimeField(blank=True, help_text="When this transaction expires", null=True),
        ),
    ]
