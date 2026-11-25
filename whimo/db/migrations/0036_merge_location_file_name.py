from django.db import migrations


class Migration(migrations.Migration):
    """Joins EFI's 0035_add_transaction_location_file_name with 0021_merge_commodity_is_archived."""

    dependencies = [
        ("db", "0021_merge_commodity_is_archived"),
        ("db", "0035_add_transaction_location_file_name"),
    ]

    operations = []
