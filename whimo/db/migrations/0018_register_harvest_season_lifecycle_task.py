from django.db import migrations


def register_transition_harvest_seasons_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="30",
        hour="3",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Transition harvest seasons",
        task="whimo.contrib.tasks.harvest_seasons.transition_harvest_seasons",
        crontab=crontab,
    )


def remove_transition_harvest_seasons_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="whimo.contrib.tasks.harvest_seasons.transition_harvest_seasons").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0017_split_harvest_season_group_fields"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(
            code=register_transition_harvest_seasons_task,
            reverse_code=remove_transition_harvest_seasons_task,
        ),
    ]
