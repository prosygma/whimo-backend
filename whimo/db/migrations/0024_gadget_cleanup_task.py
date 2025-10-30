from django.db import migrations


def register_cleanup_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="2",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Cleanup unverified gadgets",
        task="whimo.contrib.tasks.cleanup.cleanup_unverified_gadgets",
        crontab=schedule,
    )


def remove_cleanup_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Cleanup unverified gadgets").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0023_seed_commodities"),
    ]

    operations = [
        migrations.RunPython(register_cleanup_task, reverse_code=remove_cleanup_task),
    ]
