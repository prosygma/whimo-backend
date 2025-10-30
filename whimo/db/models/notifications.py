from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.common.encoders import PrettyJSONEncoder
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import BaseModel


class Notification(BaseModel):
    data = models.JSONField(null=True, blank=True, encoder=PrettyJSONEncoder, help_text=_("Notification data"))

    status = models.CharField(
        max_length=30,
        choices=[(item.value, item.name) for item in NotificationStatus],
        default=NotificationStatus.PENDING,
        help_text=_("Status of the notification"),
    )

    type = models.CharField(
        max_length=20,
        choices=[(item.value, item.name) for item in NotificationType],
        help_text=_("Type of notification"),
    )

    received_by = models.ForeignKey(
        "db.User",
        on_delete=models.PROTECT,
        related_name="received_notifications",
        help_text=_("User who received this notification"),
    )

    created_by = models.ForeignKey(
        "db.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_notifications",
        help_text=_("User who created this notification"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="notifications_history",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ("created_at",)


class NotificationSettings(BaseModel):
    user = models.ForeignKey(
        "db.User",
        on_delete=models.PROTECT,
        related_name="notification_settings",
        help_text=_("User who owns this notification settings"),
    )

    type = models.CharField(
        max_length=20,
        choices=[(item.value, item.name) for item in NotificationType],
        help_text=_("Type of notification"),
    )

    is_enabled = models.BooleanField(
        default=True,
        help_text=_("Indicates whether notifications of this type are enabled"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="notification_settings_history",
    )

    class Meta:
        db_table = "notification_settings"
        verbose_name = _("Notification Settings")
        verbose_name_plural = _("Notification Settings")
        ordering = ("user", "type")
        unique_together = ("user", "type")

    def __str__(self) -> str:
        return f"NotificationSettings: {self.user.short_id} - {self.type}"
