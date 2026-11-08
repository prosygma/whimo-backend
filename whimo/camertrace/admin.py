from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from whimo.camertrace.models import GeodataOptions, TraceabilityRule
from whimo.contrib.utils import get_admin_url


@admin.register(GeodataOptions)
class GeodataOptionsAdmin(ModelAdmin):
    fieldsets = (
        (_("Plot geodata in the mobile apps"), {"fields": ("ask_on_plot", "allow_gps_point", "allow_cicc_qr")}),
        (_("Metadata"), {"fields": ("updated_at",)}),
    )
    readonly_fields = ("updated_at",)

    def has_add_permission(self, _: HttpRequest) -> bool:
        return not GeodataOptions.objects.exists()

    def has_delete_permission(self, _: HttpRequest, __: GeodataOptions | None = None) -> bool:
        return False

    def changelist_view(self, _: HttpRequest, __: dict[str, Any] | None = None) -> HttpResponse:
        # A single row: go straight to its form.
        options = GeodataOptions.load()
        return HttpResponseRedirect(get_admin_url(GeodataOptions, "change", args=(options.pk,)))


@admin.register(TraceabilityRule)
class TraceabilityRuleAdmin(ModelAdmin):
    list_display = ("source", "traceability", "updated_at")
    list_editable = ("traceability",)
    list_display_links = None
    fields = ("source", "traceability")
    readonly_fields = ("source",)
    ordering = ("position",)

    def has_add_permission(self, _: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, _: HttpRequest, __: TraceabilityRule | None = None) -> bool:
        return False

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        extra_context = {
            **(extra_context or {}),
            "subtitle": _(
                "The status a new producer transaction gets from its geodata source. "
                "Changes apply to new transactions only."
            ),
        }
        return super().changelist_view(request, extra_context)
