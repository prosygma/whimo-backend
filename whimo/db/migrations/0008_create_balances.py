from django.db import migrations
from django.db.backends.mysql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F


def create_balances(apps: StateApps, _: DatabaseSchemaEditor) -> None:
    Transaction = apps.get_model("db", "Transaction")
    Balance = apps.get_model("db", "Balance")
    for transaction in Transaction.objects.all():
        balance, _ = Balance.objects.get_or_create(
            user=transaction.buyer,
            commodity=transaction.commodity,
        )
        balance.volume += transaction.volume
        balance.save(update_fields=["volume"])


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0007_alter_historicaltransaction_traceability_and_more"),
    ]

    operations = [
        migrations.RunPython(create_balances),
    ]
