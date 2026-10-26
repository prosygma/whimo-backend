from typing import Any

from django.contrib import admin, messages
from django.db.models import JSONField, Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import AutocompleteSelectFilter
from unfold.decorators import action, display

from whimo.contrib.utils import (
    ArchivedStatusFilter,
    NameVariantsWidget,
    ReadOnlyAdminMixin,
    change_link_with_icon,
    colored_text,
    get_admin_url,
)
from whimo.db.models import Commodity, CommodityGroup, ConversionInput, ConversionOutput, ConversionRecipe, Transaction

ARCHIVED_HIDDEN_AUTOCOMPLETE_MODELS = (ConversionInput._meta.model_name, ConversionOutput._meta.model_name)


class CommodityInline(TabularInline):
    model = Commodity
    extra = 0
    fields = ("short_id", "code", "name", "unit", "status")
    readonly_fields = ("short_id", "status")
    can_delete = False

    tab = True
    hide_title = True

    @display(description="ID")
    def short_id(self, obj: Commodity) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Status", label={"Active": "success", "Archived": "warning"})
    def status(self, obj: Commodity) -> str:
        return "Archived" if obj.is_archived else "Active"


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


class ArchiveModelAdmin(ModelAdmin, SimpleHistoryAdmin):
    actions_detail = ("archive", "restore")  # type: ignore

    def get_archive_commodities(self, obj: Any) -> QuerySet[Commodity]:
        raise NotImplementedError

    def is_restorable(self, obj: Any) -> bool:
        return obj.is_archived

    def has_archive_permission(self, request: HttpRequest, object_id: str) -> bool:
        obj = self.get_object(request, object_id)
        return obj is not None and not obj.is_archived and self.has_change_permission(request, obj)

    def has_restore_permission(self, request: HttpRequest, object_id: str) -> bool:
        obj = self.get_object(request, object_id)
        return obj is not None and self.is_restorable(obj) and self.has_change_permission(request, obj)

    @display(description="Status", label={"Active": "success", "Archived": "warning"})
    def status(self, obj: Any) -> str:
        return "Archived" if obj.is_archived else "Active"

    @action(description="Archive", permissions=["archive"])
    def archive(self, request: HttpRequest, object_id: str) -> HttpResponse:
        obj: Any = self.get_object(request, object_id)
        if request.method == "POST":
            obj.set_archived(True)
            messages.success(request, f"{obj} was archived.")
            return redirect(get_admin_url(obj, "change", args=(obj.pk,)))

        commodities = self.get_archive_commodities(obj)
        recipes = ConversionRecipe.objects.filter(
            Q(inputs__commodity__in=commodities) | Q(outputs__commodity__in=commodities)
        ).distinct()
        context = {
            **self.admin_site.each_context(request),
            "title": f"Archive {obj}",
            "opts": self.model._meta,
            "object": obj,
            "commodities_count": commodities.count(),
            "transactions_count": Transaction.objects.filter(commodity__in=commodities).count(),
            "recipes_count": recipes.count(),
        }
        return TemplateResponse(request, "admin/commodities/archive_confirm.html", context)

    @action(description="Restore", permissions=["restore"])
    def restore(self, request: HttpRequest, object_id: str) -> HttpResponse:
        obj: Any = self.get_object(request, object_id)
        obj.set_archived(False)
        messages.success(request, f"{obj} was restored.")
        return redirect(get_admin_url(obj, "change", args=(obj.pk,)))


@admin.register(CommodityGroup)
class CommodityGroupAdmin(ArchiveModelAdmin):
    formfield_overrides = {
        JSONField: {"widget": NameVariantsWidget},
    }
    list_display = ("short_id", "name", "status")
    list_filter = (ArchivedStatusFilter,)
    list_filter_submit = True
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

    def get_archive_commodities(self, obj: CommodityGroup) -> QuerySet[Commodity]:
        return obj.commodities.all()


@admin.register(Commodity)
class CommodityAdmin(ArchiveModelAdmin):
    formfield_overrides = {
        JSONField: {"widget": NameVariantsWidget},
    }
    list_display = ("short_id", "code", "name", "unit", "group_link", "status")
    list_filter = (ArchivedStatusFilter, ("group", AutocompleteSelectFilter))
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

    def get_archive_commodities(self, obj: Commodity) -> QuerySet[Commodity]:
        return Commodity.objects.filter(pk=obj.pk)

    def is_restorable(self, obj: Commodity) -> bool:
        return obj.is_archived and not obj.group.is_archived

    def get_search_results(
        self, request: HttpRequest, queryset: QuerySet[Commodity], search_term: str
    ) -> tuple[QuerySet[Commodity], bool]:
        if request.GET.get("model_name") in ARCHIVED_HIDDEN_AUTOCOMPLETE_MODELS:
            queryset = queryset.filter(is_archived=False)
        return super().get_search_results(request, queryset, search_term)
