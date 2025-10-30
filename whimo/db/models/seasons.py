from typing import cast

from django.db import models
from django.db.models import Count, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.models import BaseModel

SEASON_TRANSACTIONS_COUNT_FIELD = "_transactions_count"
_not_set = object()


class SeasonManager(models.Manager):
    def annotate_transactions_count(self) -> QuerySet["Season"]:
        return self.annotate(**{SEASON_TRANSACTIONS_COUNT_FIELD: Count("transactions")})

    def current_seasons(self) -> QuerySet["Season"]:
        today = timezone.now().date()
        return (
            self.annotate_transactions_count()
            .filter(
                start_date__lte=today,
                end_date__gte=today,
            )
            .order_by("start_date")
        )


class Season(BaseModel):
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the season"),
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text=_("Description of the season"),
    )
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Start date of the season"),
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("End date of the season"),
    )
    commodities: models.ManyToManyField = models.ManyToManyField(
        "db.Commodity",
        through="SeasonCommodity",
        related_name="seasons",
        help_text=_("Commodities participating in this season"),
    )

    objects = SeasonManager()

    @property
    def transactions_count(self) -> int:
        transactions_count = getattr(self, SEASON_TRANSACTIONS_COUNT_FIELD, _not_set)
        if transactions_count is _not_set:
            raise AttributeError("`.objects.annotate_transactions_count()` must be called to use `transactions_count`.")
        return cast(int, transactions_count)

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="seasons_history",
    )

    class Meta:
        db_table = "seasons"
        verbose_name = _("Season")
        verbose_name_plural = _("Seasons")
        ordering = ("-start_date",)

    def __str__(self) -> str:
        return self.name


class SeasonCommodity(BaseModel):
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="season_commodities",
        help_text=_("Season"),
    )
    commodity = models.ForeignKey(
        "db.Commodity",
        on_delete=models.CASCADE,
        related_name="season_commodities",
        help_text=_("Commodity"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="season_commodities_history",
    )

    class Meta:
        db_table = "season_commodities"
        verbose_name = _("Season Commodity")
        verbose_name_plural = _("Season Commodities")
        unique_together = ("season", "commodity")
        ordering = ("season", "commodity")

    def __str__(self) -> str:
        return f"{self.season.name} - {self.commodity.name}"
