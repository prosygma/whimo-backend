from django.contrib import admin
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AllValuesCheckboxFilter, AutocompleteSelectFilter, RangeDateFilter
from unfold.decorators import display

from whimo.contrib.utils import ReadOnlyAdminMixin, change_link_with_icon, colored_text, text_with_icon
from whimo.db.enums.notifications import NotificationType
from whimo.db.models.notifications import Notification


@admin.register(Notification)
class NotificationAdmin(ReadOnlyAdminMixin, ModelAdmin, SimpleHistoryAdmin):
    list_display = ("short_id", "type_labeled", "received_by_link", "created_by_link", "created_at")
    list_filter = (
        ("type", AllValuesCheckboxFilter),
        ("received_by", AutocompleteSelectFilter),
        ("created_by", AutocompleteSelectFilter),
        ("created_at", RangeDateFilter),
    )
    list_filter_submit = True
    list_select_related = ("received_by", "created_by")
    search_fields = ("id", "received_by__username", "created_by__username")
    ordering = ("-created_at",)

    fieldsets = (
        (_("Notification"), {"fields": ("type", "data", "received_by", "created_by")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    @display(description="ID", ordering="id")
    def short_id(self, obj: Notification) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(description="Received By", ordering="received_by__id", label=True)
    def received_by_link(self, obj: Notification) -> SafeString | None:
        return change_link_with_icon(obj.received_by)

    @display(description="Created By", ordering="created_by__id", label=True)
    def created_by_link(self, obj: Notification) -> SafeString | None:
        return change_link_with_icon(obj.created_by)

    @display(description="Type", ordering="type", label=True)
    def type_labeled(self, obj: Notification) -> str:
        if obj.type == NotificationType.GEODATA_MISSING:
            icon = "place"
        elif obj.type == NotificationType.TRANSACTION_PENDING:
            icon = "inbox"
        elif obj.type == NotificationType.TRANSACTION_ACCEPTED:
            icon = "refresh"
        elif obj.type == NotificationType.TRANSACTION_REJECTED:
            icon = "close"
        elif obj.type == NotificationType.TRANSACTION_EXPIRED:
            icon = "event_busy"
        else:
            icon = "question_mark"

        return text_with_icon(obj.type, icon)
