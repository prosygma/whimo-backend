import calendar
from typing import Any

from django import forms
from django.contrib import admin
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils import timezone
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelectWidget

from whimo.contrib.utils import colored_text
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import Commodity, CommodityGroup, HarvestSeason, HarvestSeasonCommodity

MONTH_CHOICES = [(month, calendar.month_name[month]) for month in range(1, 13)]


class HarvestSeasonForm(forms.ModelForm):
    commodity_group = forms.ModelChoiceField(
        queryset=CommodityGroup.objects.filter(commodities__isnull=False).distinct(),
        label=_("Commodity group"),
        help_text=_("The season covers every commodity in this group."),
        widget=UnfoldAdminSelectWidget(),
    )
    start_month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        label=_("Start month"),
        help_text=_("The month a season begins, for example September."),
        widget=UnfoldAdminSelectWidget(),
    )

    class Meta:
        model = HarvestSeason
        fields = ("commodity_group", "country", "start_month", "year", "duration_months", "status")
        labels = {
            "year": _("First year"),
            "duration_months": _("Repeats"),
        }
        help_texts = {
            "year": _(
                "The year of the season's first occurrence. Later seasons roll forward on their own "
                "after that - this doesn't need updating again.",
            ),
            "duration_months": _("How long one season lasts before the next one starts automatically."),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.instance._state.adding:
            today = timezone.now().date()
            default_start_month = self.initial.get("start_month", today.month)
            self.fields["year"].initial = today.year if default_start_month >= today.month else today.year + 1

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean() or {}
        group = cleaned_data.get("commodity_group")
        year = cleaned_data.get("year")
        start_month = cleaned_data.get("start_month")
        duration_months = cleaned_data.get("duration_months")
        if not self.instance._state.adding and group != self.instance.commodity_group:
            self.add_error("commodity_group", _("The commodity group cannot be changed after creation."))
        if group is None or not year or not start_month or not duration_months:
            return cleaned_data

        preview = HarvestSeason(year=year, start_month=start_month, duration_months=duration_months)
        preview.full_clean(exclude=["commodity_group", "name", "start_date", "end_date"], validate_constraints=False)

        conflicts = Q(period__overlap=preview.period)
        if cleaned_data.get("status") == HarvestSeasonStatus.ACTIVE:
            conflicts |= Q(status=HarvestSeasonStatus.ACTIVE)
        if (
            HarvestSeasonCommodity.objects.filter(conflicts, commodity__group=group)
            .exclude(harvest_season_id=self.instance.pk)
            .exists()
        ):
            self.add_error("commodity_group", _("Another season overlaps or is active for this group."))

        return cleaned_data


@admin.register(HarvestSeason)
class HarvestSeasonAdmin(ModelAdmin, SimpleHistoryAdmin):
    form = HarvestSeasonForm

    list_display = ("short_id", "name", "status_labeled", "country", "commodity_group", "start_date", "end_date")
    list_filter = (
        "status",
        "commodity_group",
    )
    search_fields = ("name", "country")
    ordering = ("-start_date",)

    fieldsets = (
        (
            _("Harvest Season"),
            {"fields": ("commodity_group", "country", "start_month", "year", "duration_months", "status")},
        ),
        (_("Computed"), {"fields": ("name", "start_date", "end_date")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "name", "start_date", "end_date", "created_at", "updated_at")

    def get_queryset(self, request: HttpRequest) -> QuerySet[HarvestSeason]:
        return super().get_queryset(request).select_related("commodity_group").prefetch_related("commodities")

    def save_related(self, request: HttpRequest, form: HarvestSeasonForm, formsets: list[Any], change: bool) -> None:
        with transaction.atomic():
            super().save_related(request, form, formsets, change)
            season = form.instance
            if season.harvest_season_commodities.exists():
                return
            commodity = Commodity.objects.filter(group=season.commodity_group).first()
            if commodity is None:
                return
            # HarvestSeasonCommodity.save() bulk-creates the rest of the group's commodities.
            HarvestSeasonCommodity.objects.create(
                harvest_season=season,
                commodity=commodity,
                period=season.period,
                status=season.status,
            )

    @display(description="ID", ordering="id")
    def short_id(self, obj: HarvestSeason) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(
        description="Status",
        label={
            HarvestSeasonStatus.ACTIVE.name: "success",
            HarvestSeasonStatus.PAST.name: "info",
            HarvestSeasonStatus.ARCHIVED.name: "warning",
        },
    )
    def status_labeled(self, obj: HarvestSeason) -> str:
        return HarvestSeasonStatus(obj.status).name
