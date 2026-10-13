import calendar
from datetime import date
from typing import Any, cast

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeOperators
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import BaseModel, CommodityGroup

HARVEST_SEASON_TRANSACTIONS_COUNT_FIELD = "_transactions_count"
_not_set = object()

HARVEST_SEASON_FULL_YEAR_MONTHS = 12
HARVEST_SEASON_HALF_YEAR_MONTHS = 6
HARVEST_SEASON_DURATION_CHOICES = (
    (HARVEST_SEASON_FULL_YEAR_MONTHS, _("1 year")),
    (HARVEST_SEASON_HALF_YEAR_MONTHS, _("6 months")),
)


class HarvestSeasonManager(models.Manager):
    def active_seasons(self) -> models.QuerySet["HarvestSeason"]:
        return self.filter(status=HarvestSeasonStatus.ACTIVE).annotate(
            **{HARVEST_SEASON_TRANSACTIONS_COUNT_FIELD: models.Count("transactions")},
        )


class HarvestSeason(BaseModel):
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the harvest season shown to users, computed from commodity group, year and duration"),
    )
    country = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text=_("Country this season applies to, for admin search and filtering only"),
    )
    commodity_group = models.ForeignKey(
        CommodityGroup,
        on_delete=models.PROTECT,
        related_name="harvest_seasons",
        help_text=_("Commodity group this season covers"),
    )
    year = models.PositiveSmallIntegerField(
        help_text=_("Marketing year the season starts in"),
    )
    start_month = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(1), MaxValueValidator(12)),
        help_text=_("Calendar month the season starts in"),
    )
    duration_months = models.PositiveSmallIntegerField(
        choices=HARVEST_SEASON_DURATION_CHOICES,
        default=12,
        help_text=_("Length of the season"),
    )
    start_date = models.DateField(
        help_text=_("Inclusive first date of the harvest season"),
    )
    end_date = models.DateField(
        help_text=_("Exclusive end date of the harvest season"),
    )
    status = models.CharField(
        max_length=32,
        choices=[(item.value, item.name) for item in HarvestSeasonStatus],
        default=HarvestSeasonStatus.ACTIVE,
        help_text=_("Lifecycle classification of the harvest season"),
    )
    commodities: models.ManyToManyField = models.ManyToManyField(
        "db.Commodity",
        through="HarvestSeasonCommodity",
        related_name="harvest_seasons",
        help_text=_("Commodities covered by this harvest season"),
    )

    objects = HarvestSeasonManager()

    @property
    def end_month(self) -> int:
        return (self.start_month - 1 + self.duration_months - 1) % 12 + 1

    @property
    def transactions_count(self) -> int:
        transactions_count = getattr(self, HARVEST_SEASON_TRANSACTIONS_COUNT_FIELD, _not_set)
        if transactions_count is _not_set:
            raise AttributeError("`.objects.active_seasons()` must be called to use `transactions_count`.")
        return cast(int, transactions_count)

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="harvest_seasons_history",
    )

    class Meta:
        db_table = "harvest_seasons"
        verbose_name = _("Harvest Season")
        verbose_name_plural = _("Harvest Seasons")
        ordering = ("-start_date",)
        constraints = (
            models.CheckConstraint(
                condition=Q(start_date__lt=models.F("end_date")),
                name="harvest_season_start_before_end",
            ),
            models.UniqueConstraint(
                fields=("commodity_group",),
                condition=Q(status=HarvestSeasonStatus.ACTIVE),
                name="harvest_season_group_single_active",
            ),
            models.UniqueConstraint(
                fields=("commodity_group",),
                condition=Q(status=HarvestSeasonStatus.PAST),
                name="harvest_season_group_single_past",
            ),
        )

    def __str__(self) -> str:
        return self.name

    def full_clean(self, *args: Any, **kwargs: Any) -> None:
        # Runs before Django's own field-level required checks, so start_date/end_date/name
        # (derived, not user-supplied) are already filled in by the time those checks run.
        self._sync_period_and_name()
        super().full_clean(*args, **kwargs)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._sync_period_and_name()
        with transaction.atomic():
            super().save(*args, **kwargs)
            self.harvest_season_commodities.update(period=self.period, status=self.status)

    @property
    def period(self) -> tuple[date, date]:
        return self.start_date, self.end_date

    def _sync_period_and_name(self) -> None:
        months_given = bool(self.year) and bool(self.start_month)
        dates_given = bool(self.start_date) and bool(self.end_date)

        if months_given and not dates_given:
            self.start_date = date(self.year, self.start_month, 1)
            self.end_date = self._shift_months(self.start_date, self.duration_months)
        elif dates_given and not months_given:
            span = (self.end_date.year - self.start_date.year) * 12 + (self.end_date.month - self.start_date.month)
            if span not in dict(HARVEST_SEASON_DURATION_CHOICES):
                raise ValidationError({"end_date": _("A harvest season must be either 6 or 12 months long.")})
            self.year = self.start_date.year
            self.start_month = self.start_date.month
            self.duration_months = span
        elif months_given and dates_given:
            expected_start = date(self.year, self.start_month, 1)
            expected_end = self._shift_months(expected_start, self.duration_months)
            if (self.start_date, self.end_date) != (expected_start, expected_end):
                raise ValidationError(_("The season's dates do not match its year, start month and duration."))
        else:
            return

        if self.commodity_group_id:
            self.name = self._build_name()

    @staticmethod
    def _shift_months(start: date, months: int) -> date:
        month_index = start.month - 1 + months
        return date(start.year + month_index // 12, month_index % 12 + 1, start.day)

    def _build_name(self) -> str:
        group_name = self.commodity_group.name
        if self.duration_months == HARVEST_SEASON_FULL_YEAR_MONTHS:
            return f"{group_name} {self.year}/{str(self.year + 1)[-2:]}"
        return f"{group_name} {calendar.month_abbr[self.start_month]}-{calendar.month_abbr[self.end_month]} {self.year}"


class HarvestSeasonCommodity(BaseModel):
    harvest_season = models.ForeignKey(
        HarvestSeason,
        on_delete=models.CASCADE,
        related_name="harvest_season_commodities",
        help_text=_("Harvest season"),
    )
    commodity = models.ForeignKey(
        "db.Commodity",
        on_delete=models.CASCADE,
        related_name="harvest_season_commodities",
        help_text=_("Commodity"),
    )
    period = DateRangeField(
        help_text=_("Dates of the harvest season, kept in sync for the overlap constraint"),
    )
    status = models.CharField(
        max_length=32,
        choices=[(item.value, item.name) for item in HarvestSeasonStatus],
        help_text=_("Status of the harvest season, kept in sync for the single active constraint"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="harvest_season_commodities_history",
    )

    class Meta:
        db_table = "harvest_season_commodities"
        verbose_name = _("Harvest Season Commodity")
        verbose_name_plural = _("Harvest Season Commodities")
        ordering = ("harvest_season", "commodity")
        constraints = (
            models.UniqueConstraint(
                fields=("harvest_season", "commodity"),
                name="harvest_season_commodity_unique",
            ),
            models.UniqueConstraint(
                fields=("commodity",),
                condition=Q(status=HarvestSeasonStatus.ACTIVE),
                name="harvest_season_commodity_single_active",
            ),
            ExclusionConstraint(
                name="harvest_season_commodity_no_overlap",
                expressions=(
                    ("period", RangeOperators.OVERLAPS),
                    ("commodity", RangeOperators.EQUAL),
                ),
            ),
        )

    def __str__(self) -> str:
        return f"{self.harvest_season.name} - {self.commodity.name}"

    def clean(self) -> None:
        super().clean()

        if not self.harvest_season_id or not self.commodity_id:
            return

        if self.commodity.group_id != self.harvest_season.commodity_group_id:
            raise ValidationError({"commodity": _("This commodity does not belong to the season's commodity group.")})

        self._apply_harvest_season()

        conflicts = Q(period__overlap=self.period)
        if self.status == HarvestSeasonStatus.ACTIVE:
            conflicts |= Q(status=HarvestSeasonStatus.ACTIVE)

        conflicting = (
            HarvestSeasonCommodity.objects.filter(
                conflicts,
                commodity__group_id=self.commodity.group_id,
            )
            .exclude(harvest_season_id=self.harvest_season_id)
            .exists()
        )
        if conflicting:
            raise ValidationError({"commodity": _("Another harvest season overlaps or is active for this group.")})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self._apply_harvest_season()
        with transaction.atomic():
            if not self._state.adding:
                previous = HarvestSeasonCommodity.objects.get(pk=self.pk)
                if previous.harvest_season_id != self.harvest_season_id or previous.commodity_id != self.commodity_id:
                    raise ValidationError(_("Harvest season coverage cannot be moved."))
            CommodityGroup.objects.select_for_update().get(pk=self.commodity.group_id)
            super().save(*args, **kwargs)
            commodities = self.commodity.group.commodities.exclude(
                harvest_season_commodities__harvest_season_id=self.harvest_season_id,
            )
            HarvestSeasonCommodity.objects.bulk_create(
                HarvestSeasonCommodity(
                    harvest_season=self.harvest_season,
                    commodity=commodity,
                    period=self.period,
                    status=self.status,
                )
                for commodity in commodities
            )

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        harvest_season_id = self.harvest_season_id
        group_id = self.commodity.group_id
        with transaction.atomic():
            total, deleted = super().delete(*args, **kwargs)
            related_total, related_deleted = HarvestSeasonCommodity.objects.filter(
                harvest_season_id=harvest_season_id,
                commodity__group_id=group_id,
            ).delete()
            for model, count in related_deleted.items():
                deleted[model] = deleted.get(model, 0) + count
            return total + related_total, deleted

    def _apply_harvest_season(self) -> None:
        self.period = self.harvest_season.period
        self.status = self.harvest_season.status
