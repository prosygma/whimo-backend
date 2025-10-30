from django.contrib import admin
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from unfold.decorators import display

from whimo.contrib.utils import ReadOnlyAdminMixin, change_link_with_icon, colored_text
from whimo.db.models import Balance


@admin.register(Balance)
class BalanceAdmin(ReadOnlyAdminMixin, ModelAdmin, SimpleHistoryAdmin):
    list_display = ("short_id", "user_link", "commodity_link", "volume")
    list_filter = (
        ("user", AutocompleteSelectFilter),
        ("commodity", AutocompleteSelectFilter),
    )
    list_filter_submit = True
    list_select_related = ("user", "commodity")
    search_fields = ("id", "user__username", "commodity__name", "commodity__code")
    ordering = ("user__id", "commodity__name", "commodity__code")

    fieldsets = (
        (_("Balance"), {"fields": ("user", "commodity", "volume")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user", "commodity")

    @display(description="ID", ordering="id")
    def short_id(self, obj: Balance) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(description="Commodity", ordering="commodity__name", label=True)
    def commodity_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="User", ordering="user__id", label=True)
    def user_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.user)
