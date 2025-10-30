from django.contrib import admin
from django.db.models import JSONField, QuerySet
from django.http import HttpRequest
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from unfold.decorators import display

from whimo.contrib.utils import ArrayJSONWidget, ReadOnlyAdminMixin, change_link_with_icon, colored_text
from whimo.db.models import Commodity, CommodityGroup, Transaction


class CommodityInline(TabularInline):
    model = Commodity
    extra = 0
    fields = ("short_id", "code", "name", "name_variants", "unit")
    readonly_fields = ("short_id",)
    can_delete = False

    tab = True
    hide_title = True

    @display(description="ID")
    def short_id(self, obj: Commodity) -> SafeString | None:
        return change_link_with_icon(obj)


class TransactionInline(ReadOnlyAdminMixin, TabularInline):
    model = Transaction
    extra = 0
    fields = ("short_id", "type", "status", "traceability", "seller_link", "buyer_link", "created_at")
    readonly_fields = ("short_id", "seller_link", "buyer_link", "created_at")

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Transaction]:
        return super().get_queryset(request).select_related("seller", "buyer")

    @display(description="ID")
    def short_id(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Seller", label=True)
    def seller_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.seller)

    @display(description="Buyer", label=True)
    def buyer_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.buyer)


@admin.register(CommodityGroup)
class CommodityGroupAdmin(ModelAdmin, SimpleHistoryAdmin):
    formfield_overrides = {
        JSONField: {"widget": ArrayJSONWidget},
    }
    list_display = ("short_id", "name")
    search_fields = ("id", "name", "name_variants")
    ordering = ("name",)

    fieldsets = (
        (_("Commodity Group"), {"fields": ("name", "name_variants")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (CommodityInline,)

    @display(description="ID", ordering="id")
    def short_id(self, obj: CommodityGroup) -> str:
        return colored_text(obj.short_id)


@admin.register(Commodity)
class CommodityAdmin(ModelAdmin, SimpleHistoryAdmin):
    formfield_overrides = {
        JSONField: {"widget": ArrayJSONWidget},
    }
    list_display = ("short_id", "code", "name", "unit", "group_link")
    list_filter = (("group", AutocompleteSelectFilter),)
    list_filter_submit = True
    list_select_related = ("group",)
    search_fields = ("id", "code", "name", "name_variants", "unit", "group__name")
    ordering = ("group", "name")

    fieldsets = (
        (_("Commodity"), {"fields": ("code", "name", "name_variants", "unit")}),
        (_("Commodity Group"), {"fields": ("group",)}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("group",)
    inlines = (TransactionInline,)

    @display(description="ID", ordering="id")
    def short_id(self, obj: Commodity) -> str:
        return colored_text(obj.short_id)

    @display(description="Group", ordering="group__name", label=True)
    def group_link(self, obj: Commodity) -> SafeString | None:
        return change_link_with_icon(obj.group, text=obj.group.name)
