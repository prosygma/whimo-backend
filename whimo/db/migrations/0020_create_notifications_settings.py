from django.db import migrations
from django.db.backends.mysql.schema import DatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F

from whimo.db.enums.notifications import NotificationType


def create_notification_settings(apps: StateApps, _: DatabaseSchemaEditor) -> None:
    NotificationSettings = apps.get_model("db", "NotificationSettings")
    User = apps.get_model("db", "User")
    for user in User.objects.all():
        for notification_type in NotificationType:
            NotificationSettings.objects.get_or_create(user=user, type=notification_type)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0019_notificationsettings"),
    ]

    operations = [
        migrations.RunPython(create_notification_settings),
    ]
