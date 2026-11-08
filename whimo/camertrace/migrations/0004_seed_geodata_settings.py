from typing import Any

from django.db import migrations

# Frozen copy: later edits to the model defaults must not change what this migration seeds.
DEFAULT_RULES = (
    ("cicc_qr", "full"),
    ("qr", "conditional"),
    ("gps", "conditional"),
    ("file", "conditional"),
    ("manual", "partial"),
    ("none_from_farmer", "partial"),
    ("none", "incomplete"),
)


def seed(apps: Any, _: Any) -> None:
    rule_model = apps.get_model("camertrace", "TraceabilityRule")
    for position, (source, traceability) in enumerate(DEFAULT_RULES):
        rule_model.objects.get_or_create(source=source, defaults={"traceability": traceability, "position": position})
    options_model = apps.get_model("camertrace", "GeodataOptions")
    if not options_model.objects.exists():
        options_model.objects.create()

    from django.core.cache import cache  # noqa: PLC0415

    cache.delete_many(["camertrace:geodata_options", "camertrace:traceability_rules"])


class Migration(migrations.Migration):
    dependencies = [("camertrace", "0003_geodata_options")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
