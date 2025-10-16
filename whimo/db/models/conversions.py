from typing import cast

from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.models.base import BaseModel

_not_set = object()

RECIPE_INPUTS_FIELD = "_prefetched_inputs"
RECIPE_OUTPUTS_FIELD = "_prefetched_outputs"


class ConversionRecipeManager(models.Manager):
    def prefetch_conversion_data(self) -> QuerySet["ConversionRecipe"]:
        queryset = self.prefetch_related(
            models.Prefetch(
                "inputs",
                queryset=ConversionInput.objects.select_related("commodity__group"),
                to_attr=RECIPE_INPUTS_FIELD,
            ),
            models.Prefetch(
                "outputs",
                queryset=ConversionOutput.objects.select_related("commodity__group"),
                to_attr=RECIPE_OUTPUTS_FIELD,
            ),
        )
        return cast(QuerySet, queryset)


class ConversionRecipe(BaseModel):
    name = models.CharField(
        max_length=255,
        help_text=_("Name or description of this conversion recipe"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="conversion_recipes_history",
    )

    objects: ConversionRecipeManager = ConversionRecipeManager()

    @property
    def inputs_list(self) -> list["ConversionInput"]:
        inputs = getattr(self, RECIPE_INPUTS_FIELD, _not_set)
        if inputs is _not_set:
            raise AttributeError("`.objects.prefetch_conversion_data()` must be called to use `inputs_list`.")
        return cast(list, inputs)

    @property
    def outputs_list(self) -> list["ConversionOutput"]:
        outputs = getattr(self, RECIPE_OUTPUTS_FIELD, _not_set)
        if outputs is _not_set:
            raise AttributeError("`.objects.prefetch_conversion_data()` must be called to use `outputs_list`.")
        return cast(list, outputs)

    class Meta:
        db_table = "conversion_recipes"
        verbose_name = _("Conversion Recipe")
        verbose_name_plural = _("Conversion Recipes")
        ordering = ("-created_at",)


class ConversionInput(BaseModel):
    recipe = models.ForeignKey(
        "ConversionRecipe",
        on_delete=models.CASCADE,
        related_name="inputs",
        help_text=_("Conversion recipe"),
    )
    commodity = models.ForeignKey(
        "Commodity",
        on_delete=models.CASCADE,
        related_name="conversion_inputs",
        help_text=_("Input commodity"),
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        help_text=_("Quantity of this commodity required as input"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="conversion_inputs_history",
    )

    class Meta:
        db_table = "conversion_inputs"
        verbose_name = _("Conversion Input")
        verbose_name_plural = _("Conversion Inputs")
        ordering = ("recipe", "commodity")
        unique_together = [("recipe", "commodity")]


class ConversionOutput(BaseModel):
    recipe = models.ForeignKey(
        "ConversionRecipe",
        on_delete=models.CASCADE,
        related_name="outputs",
        help_text=_("Conversion recipe"),
    )
    commodity = models.ForeignKey(
        "Commodity",
        on_delete=models.CASCADE,
        related_name="conversion_outputs",
        help_text=_("Output commodity"),
    )
    quantity = models.DecimalField(
        max_digits=15,
        decimal_places=6,
        help_text=_("Quantity of this commodity produced as output"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="conversion_outputs_history",
    )

    class Meta:
        db_table = "conversion_outputs"
        verbose_name = _("Conversion Output")
        verbose_name_plural = _("Conversion Outputs")
        ordering = ("recipe", "commodity")
        unique_together = [("recipe", "commodity")]
