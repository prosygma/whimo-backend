from django.core.cache import cache
from django.db import migrations

# Cameroon uses French and English: French is the default and Spanish is not offered.
# Runs once; administrators can change it afterwards in the admin (Languages).


def french_and_english(apps, schema_editor) -> None:
    Language = apps.get_model("languages", "Language")
    Language.objects.filter(code="es").update(is_enabled=False, is_default=False)
    Language.objects.exclude(code="fr").update(is_default=False)
    Language.objects.filter(code="fr").update(is_enabled=True, is_default=True, position=1)
    Language.objects.filter(code="en").update(is_enabled=True, position=2)
    cache.delete("languages:enabled")  # update() sends no signal: drop the cached list


class Migration(migrations.Migration):
    dependencies = [
        ("languages", "0002_builtin_languages"),
    ]

    operations = [
        migrations.RunPython(french_and_english, migrations.RunPython.noop),
    ]
