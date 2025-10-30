from typing import Any

from django.db import migrations


def register_season_distribution_task(apps: Any, _schema_editor: Any) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Distribute transactions over seasons",
        task="whimo.contrib.tasks.season_distribution.distribute_transactions_over_seasons",
        crontab=schedule,
    )


def remove_season_distribution_task(apps: Any, _schema_editor: Any) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Distribute transactions over seasons").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0027_harvest_season"),
    ]

    operations = [
        migrations.RunPython(register_season_distribution_task, reverse_code=remove_season_distribution_task),
    ]
