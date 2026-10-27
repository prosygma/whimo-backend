from django.contrib import admin
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from unfold.decorators import display

from whimo.contrib.utils import HarvestSeasonStatusFilter, ReadOnlyAdminMixin, change_link_with_icon, colored_text
from whimo.db.enums.harvest_seasons import HarvestSeasonStatus
from whimo.db.models import Balance


@admin.register(Balance)
class BalanceAdmin(ReadOnlyAdminMixin, ModelAdmin, SimpleHistoryAdmin):
    list_display = (
        "short_id",
        "user_link",
        "commodity_link",
        "harvest_season_link",
        "harvest_season_status_labeled",
        "volume",
    )
    list_filter = (
        ("user", AutocompleteSelectFilter),
        ("commodity", AutocompleteSelectFilter),
        ("harvest_season", AutocompleteSelectFilter),
        ("harvest_season__status", HarvestSeasonStatusFilter),
    )
    list_filter_submit = True
    list_select_related = ("user", "commodity", "harvest_season")
    search_fields = ("id", "user__username", "commodity__name", "commodity__code", "harvest_season__name")
    ordering = ("user__id", "commodity__name", "commodity__code", "-harvest_season__start_date")

    fieldsets = (
        (_("Balance"), {"fields": ("user", "commodity", "harvest_season", "volume")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user", "commodity", "harvest_season")

    @display(description="ID", ordering="id")
    def short_id(self, obj: Balance) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(description="Commodity", ordering="commodity__name", label=True)
    def commodity_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="User", ordering="user__id", label=True)
    def user_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.user)

    @display(description="Harvest Season", ordering="harvest_season__start_date", label=True)
    def harvest_season_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.harvest_season, text=str(obj.harvest_season))

    @display(
        description="Season Status",
        ordering="harvest_season__status",
        label={
            HarvestSeasonStatus.ACTIVE.name: "success",
            HarvestSeasonStatus.PAST.name: "info",
            HarvestSeasonStatus.ARCHIVED.name: "warning",
        },
    )
    def harvest_season_status_labeled(self, obj: Balance) -> str:
        return HarvestSeasonStatus(obj.harvest_season.status).name
