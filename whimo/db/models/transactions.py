from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.enums import TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import BaseModel


class Transaction(BaseModel):
    type = models.CharField(
        max_length=20,
        choices=[(item.value, item.name) for item in TransactionType],
        help_text=_("Type of transaction"),
    )

    group_id = models.UUIDField(
        null=True,
        blank=True,
        help_text=_("Transaction group id"),
    )

    location = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        choices=[(item.value, item.name) for item in TransactionLocation],
        help_text=_("Source of location geodata"),
    )

    status = models.CharField(
        max_length=20,
        choices=[(item.value, item.name) for item in TransactionStatus],
        default=TransactionStatus.PENDING,
        help_text=_("Status of the transaction"),
    )

    traceability = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[(item.value, item.name) for item in TransactionTraceability],
        help_text=_("Traceability status of the transaction"),
    )

    transaction_latitude = models.DecimalField(
        max_digits=9,
        null=True,
        blank=True,
        decimal_places=6,
        help_text=_("Transaction latitude coordinate"),
    )

    transaction_longitude = models.DecimalField(
        max_digits=9,
        null=True,
        blank=True,
        decimal_places=6,
        help_text=_("Transaction longitude coordinate"),
    )

    farm_latitude = models.DecimalField(
        max_digits=9,
        null=True,
        blank=True,
        decimal_places=6,
        help_text=_("Farm latitude coordinate"),
    )

    farm_longitude = models.DecimalField(
        max_digits=9,
        null=True,
        blank=True,
        decimal_places=6,
        help_text=_("Farm longitude coordinate"),
    )

    commodity = models.ForeignKey(
        "db.Commodity",
        on_delete=models.PROTECT,
        related_name="transactions",
        help_text=_("Commodity being traded"),
    )

    volume = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text=_("Volume of commodities"),
    )

    seller = models.ForeignKey(
        "db.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="sold",
        help_text=_("Seller in this transaction"),
    )

    buyer = models.ForeignKey(
        "db.User",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="bought",
        help_text=_("Buyer in this transaction"),
    )

    created_by = models.ForeignKey(
        "db.User",
        on_delete=models.PROTECT,
        related_name="created_transactions",
        help_text=_("User who created this transaction"),
    )

    season = models.ForeignKey(
        "db.Season",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transactions",
        help_text=_("Season this transaction belongs to"),
    )

    is_buying_from_farmer = models.BooleanField(
        default=False,
        help_text=_("Whether this transaction is buying from a farmer directly"),
    )

    is_automatic = models.BooleanField(
        default=False,
        help_text=_("Whether this transaction was created automatically"),
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this transaction expires"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="transactions_history",
    )

    class Meta:
        db_table = "transactions"
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        ordering = ("-created_at", "-commodity_id")
