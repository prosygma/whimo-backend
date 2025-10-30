from django.db import migrations
from django.db.backends.mysql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F


def migrate_transaction_created_by(apps: StateApps, _: DatabaseSchemaEditor) -> None:
    Transaction = apps.get_model("db", "Transaction")
    Transaction.objects.all().update(created_by_id=F("buyer_id"))


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0002_transaction_created_by"),
    ]

    operations = [
        migrations.RunPython(migrate_transaction_created_by),
    ]
