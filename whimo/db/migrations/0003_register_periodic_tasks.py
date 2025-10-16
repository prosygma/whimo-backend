from django.db import migrations


def register_expire_transactions_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="*",
        hour="*",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Expire transactions",
        task="whimo.contrib.tasks.transactions.expire_transactions",
        crontab=crontab,
    )


def remove_expire_transactions_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="whimo.contrib.tasks.transactions.expire_transactions").delete()


def register_cleanup_unverified_gadgets_task(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="2",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Cleanup unverified gadgets",
        task="whimo.contrib.tasks.cleanup.cleanup_unverified_gadgets",
        crontab=crontab,
    )


def remove_cleanup_unverified_gadgets_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(task="whimo.contrib.tasks.cleanup.cleanup_unverified_gadgets").delete()


def register_distribute_transactions_over_seasons_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    crontab, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="*",
        day_of_month="*",
        month_of_year="*",
        day_of_week="*",
    )

    PeriodicTask.objects.get_or_create(
        name="Distribute transactions over seasons",
        task="whimo.contrib.tasks.season_distribution.distribute_transactions_over_seasons",
        crontab=crontab,
    )


def remove_distribute_transactions_over_seasons_task(apps, schema_editor) -> None:
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        task="whimo.contrib.tasks.season_distribution.distribute_transactions_over_seasons",
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0002_populate_commodities"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(
            code=register_expire_transactions_task,
            reverse_code=remove_expire_transactions_task,
        ),
        migrations.RunPython(
            code=register_cleanup_unverified_gadgets_task,
            reverse_code=remove_cleanup_unverified_gadgets_task,
        ),
        migrations.RunPython(
            code=register_distribute_transactions_over_seasons_task,
            reverse_code=remove_distribute_transactions_over_seasons_task,
        ),
    ]
