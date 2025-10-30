from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.models import BaseModel


class Balance(BaseModel):
    volume = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commodity = models.ForeignKey(
        "db.Commodity",
        on_delete=models.PROTECT,
        help_text=_("Balance commodity"),
    )
    user = models.ForeignKey(
        "db.User",
        on_delete=models.PROTECT,
        help_text=_("Balance user"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="balances_history",
    )

    class Meta:
        db_table = "balances"
        verbose_name = _("Balance")
        verbose_name_plural = _("Balances")
