import django.db.models.deletion
import simple_history.models
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0018_alter_historicalnotification_type_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalNotificationSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True, help_text="Indicates whether notifications of this type are enabled"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="User who owns this notification settings",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical Notification Settings",
                "verbose_name_plural": "historical Notification Settings",
                "db_table": "notification_settings_history",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="NotificationSettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier for this record.",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created."),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, help_text="Timestamp when this record was last updated."),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("transaction_pending", "TRANSACTION_PENDING"),
                            ("transaction_accepted", "TRANSACTION_ACCEPTED"),
                            ("transaction_rejected", "TRANSACTION_REJECTED"),
                            ("transaction_expired", "TRANSACTION_EXPIRED"),
                            ("geodata_missing", "GEODATA_MISSING"),
                            ("geodata_updated", "GEODATA_UPDATED"),
                        ],
                        help_text="Type of notification",
                        max_length=20,
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True, help_text="Indicates whether notifications of this type are enabled"
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        help_text="User who owns this notification settings",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="notification_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification Settings",
                "verbose_name_plural": "Notification Settings",
                "db_table": "notification_settings",
                "ordering": ("user", "type"),
                "unique_together": {("user", "type")},
            },
        ),
    ]
