from django.db import migrations


class Migration(migrations.Migration):
    """Joins EFI's 0005-0018 with 0005_whatsapp_settings, already applied in production."""

    dependencies = [
        ("db", "0005_whatsapp_settings"),
        ("db", "0018_register_harvest_season_lifecycle_task"),
    ]

    operations = []
