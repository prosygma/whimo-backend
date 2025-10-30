from django.db import migrations


def register_tasks(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")

    PeriodicTask.objects.get_or_create(
        crontab=CrontabSchedule.objects.create(
            minute="*",
            hour="*",
            day_of_month="*",
            month_of_year="*",
            day_of_week="*",
        ),
        name="Expire transactions",
        task="whimo.contrib.tasks.transactions.expire_transactions",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0014_historicaltransaction_expires_at_and_more"),
    ]

    operations = [
        migrations.RunPython(register_tasks),
    ]
