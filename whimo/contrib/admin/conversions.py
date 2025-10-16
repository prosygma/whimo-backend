from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from unfold.sections import TableSection

from whimo.contrib.utils import colored_text
from whimo.db.models import ConversionInput, ConversionOutput, ConversionRecipe


class ConversionInputInline(TabularInline):
    model = ConversionInput
    extra = 0
    fields = ("commodity", "quantity")
    autocomplete_fields = ("commodity",)

    hide_title = True


class ConversionOutputInline(TabularInline):
    model = ConversionOutput
    extra = 0
    fields = ("commodity", "quantity")
    autocomplete_fields = ("commodity",)

    hide_title = True


class ConversionInputsSection(TableSection):
    verbose_name = _("Inputs")  # type: ignore[assignment]
    related_name = "inputs"  # type: ignore[assignment]
    fields = ("code", "name", "unit", "quantity")  # type: ignore[assignment]

    def code(self, instance: ConversionInput) -> str:
        return instance.commodity.code

    def name(self, instance: ConversionInput) -> str:
        return instance.commodity.name

    def unit(self, instance: ConversionInput) -> str:
        return instance.commodity.unit


class ConversionOutputsSection(TableSection):
    verbose_name = _("Outputs")  # type: ignore[assignment]
    related_name = "outputs"  # type: ignore[assignment]
    fields = ("code", "name", "unit", "quantity")  # type: ignore[assignment]

    def code(self, instance: ConversionOutput) -> str:
        return instance.commodity.code

    def name(self, instance: ConversionOutput) -> str:
        return instance.commodity.name

    def unit(self, instance: ConversionOutput) -> str:
        return instance.commodity.unit


@admin.register(ConversionRecipe)
class ConversionRecipeAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ("short_id", "name", "created_at")
    list_sections = (ConversionInputsSection, ConversionOutputsSection)
    search_fields = ("id", "name")
    ordering = ("-created_at",)

    fieldsets = (
        (_("Conversion Recipe"), {"fields": ("name",)}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (ConversionInputInline, ConversionOutputInline)

    def get_queryset(self, request: HttpRequest) -> QuerySet[ConversionRecipe]:
        return super().get_queryset(request).prefetch_related("inputs__commodity", "outputs__commodity")

    @display(description="ID", ordering="id")
    def short_id(self, obj: ConversionRecipe) -> str:
        return colored_text(obj.short_id)
