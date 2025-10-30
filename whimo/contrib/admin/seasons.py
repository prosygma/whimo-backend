from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from whimo.contrib.utils import ReadOnlyAdminMixin, change_link_with_icon, colored_text
from whimo.db.models import Season, SeasonCommodity, Transaction


class SeasonCommodityInline(TabularInline):
    model = SeasonCommodity
    extra = 0
    fields = ("commodity",)
    autocomplete_fields = ("commodity",)

    tab = True
    hide_title = True


class SeasonTransactionInline(ReadOnlyAdminMixin, TabularInline):
    model = Transaction
    fk_name = "season"
    extra = 0
    fields = ("short_id", "type", "status", "traceability", "commodity_link", "seller_link", "buyer_link", "created_at")
    readonly_fields = ("short_id", "commodity_link", "seller_link", "buyer_link", "created_at")
    verbose_name_plural = "Transactions"

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Transaction]:
        return super().get_queryset(request).select_related("commodity", "seller", "buyer")

    @display(description="ID")
    def short_id(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Commodity", label=True)
    def commodity_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="Seller", label=True)
    def seller_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.seller)

    @display(description="Buyer", label=True)
    def buyer_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.buyer)


@admin.register(Season)
class SeasonAdmin(ModelAdmin, SimpleHistoryAdmin):
    inlines = (SeasonCommodityInline, SeasonTransactionInline)

    list_display = ("short_id", "name", "status_labeled", "start_date", "end_date")
    list_filter = (
        ("start_date", RangeDateFilter),
        ("end_date", RangeDateFilter),
    )
    search_fields = ("name", "description")
    ordering = ("-end_date", "-start_date")

    fieldsets = (
        (_("Season"), {"fields": ("name", "description", "start_date", "end_date")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Season]:
        return super().get_queryset(request).prefetch_related("commodities", "transactions")

    @display(description="ID", ordering="id")
    def short_id(self, obj: Season) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(
        description="Status",
        label={
            "Upcoming": "warning",
            "Active": "success",
            "Completed": "info",
        },
    )
    def status_labeled(self, obj: Season) -> str:
        today = timezone.now().date()

        if obj.start_date and today < obj.start_date:
            return "Upcoming"

        if obj.end_date and today > obj.end_date:
            return "Completed"

        return "Active"
