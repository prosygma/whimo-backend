from decimal import Decimal
from typing import cast
from uuid import UUID

from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Exists, OuterRef, QuerySet, Subquery
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.models import Balance, BaseModel

COMMODITY_BALANCE_FIELD = "_balance"
COMMODITY_HAS_RECIPE_FIELD = "_has_recipe"
_not_set = object()


class CommodityManager(models.Manager):
    def annotate_balances(self, user_id: UUID) -> QuerySet["Commodity"]:
        balance_subquery = Balance.objects.filter(user_id=user_id, commodity=OuterRef("pk")).values("volume")[:1]
        return (
            self.annotate_has_recipe()
            .select_related("group")
            .annotate(**{COMMODITY_BALANCE_FIELD: Subquery(balance_subquery)})
        )

    def annotate_has_recipe(self) -> QuerySet["Commodity"]:
        from whimo.db.models import ConversionInput

        has_recipe_subquery = Exists(ConversionInput.objects.filter(commodity=OuterRef("pk")))
        return self.annotate(**{COMMODITY_HAS_RECIPE_FIELD: has_recipe_subquery})


class CommodityGroup(BaseModel):
    name = models.CharField(max_length=50, help_text=_("Name of the commodity group"))
    name_variants = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Alternative name variations and translations"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
            "name_variants",
        ),
        table_name="commodity_groups_history",
    )

    class Meta:
        db_table = "commodity_groups"
        verbose_name = _("Commodity Group")
        verbose_name_plural = _("Commodity Groups")
        ordering = ("name",)
        indexes = [
            GinIndex(fields=["name_variants"], name="db_commgrp_name_vars_gin_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Commodity(BaseModel):
    code = models.CharField(max_length=20, unique=True, help_text=_("Commodity code"))
    name = models.CharField(max_length=255, help_text=_("Name of the commodity"))
    name_variants = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Alternative name variations and translations"),
    )
    unit = models.CharField(max_length=10, help_text=_("Unit of measurement"))
    group = models.ForeignKey(
        CommodityGroup,
        on_delete=models.PROTECT,
        related_name="commodities",
        help_text=_("Commodity group"),
    )

    objects = CommodityManager()

    @property
    def balance(self) -> Decimal | None:
        balance = getattr(self, COMMODITY_BALANCE_FIELD, _not_set)
        if balance is _not_set:
            raise AttributeError("`.objects.annotate_balances` must be called to use `balance`.")
        return cast(Decimal | None, balance)

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
            "name_variants",
        ),
        table_name="commodities_history",
    )

    class Meta:
        db_table = "commodities"
        verbose_name = _("Commodity")
        verbose_name_plural = _("Commodities")
        ordering = ("code",)
        indexes = [
            GinIndex(fields=["name_variants"], name="db_comm_name_vars_gin_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.name} ({self.unit})"
