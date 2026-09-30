from django.db import migrations

# The languages the apps ship strings for. Administrators can disable them, change the
# default or add others in the admin (Languages).
BUILTIN = (
    ("en", "English", "English", True, 1),
    ("fr", "Français", "French", False, 2),
    ("es", "Español", "Spanish", False, 3),
)


def create_languages(apps, schema_editor) -> None:
    Language = apps.get_model("languages", "Language")
    for code, name, english_name, is_default, position in BUILTIN:
        Language.objects.get_or_create(
            code=code,
            defaults={"name": name, "english_name": english_name, "is_default": is_default, "position": position},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("languages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_languages, migrations.RunPython.noop),
    ]
