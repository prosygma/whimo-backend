from django.db import migrations


class Migration(migrations.Migration):
    """Joins EFI's 0020_add_commodity_is_archived with 0019_merge_whatsapp_settings."""

    dependencies = [
        ("db", "0019_merge_whatsapp_settings"),
        ("db", "0020_add_commodity_is_archived"),
    ]

    operations = []
