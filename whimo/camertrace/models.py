from django.db import models
from django.utils.translation import gettext_lazy as _

from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models.base import BaseModel


class GeodataSource(models.TextChoices):
    """Where the plot geodata of a producer transaction comes from, as rated by `TraceabilityRule`."""

    CICC_QR = "cicc_qr", _("CICC QR code (certified geometer)")
    QR = "qr", _("GeoJSON QR code")
    GPS = "gps", _("Device GPS, on the plot")
    FILE = "file", _("Uploaded file")
    MANUAL = "manual", _("Point picked on the map")
    NONE_FROM_FARMER = "none_from_farmer", _("No geodata, bought from a farmer")
    NONE = "none", _("No geodata")


DEFAULT_TRACEABILITY = {
    GeodataSource.CICC_QR: TransactionTraceability.FULL,
    GeodataSource.QR: TransactionTraceability.CONDITIONAL,
    GeodataSource.GPS: TransactionTraceability.CONDITIONAL,
    GeodataSource.FILE: TransactionTraceability.CONDITIONAL,
    GeodataSource.MANUAL: TransactionTraceability.PARTIAL,
    GeodataSource.NONE_FROM_FARMER: TransactionTraceability.PARTIAL,
    GeodataSource.NONE: TransactionTraceability.INCOMPLETE,
}


class GeodataOptions(BaseModel):
    """Geodata choices offered by the mobile apps. Single row (see `load`)."""

    ask_on_plot = models.BooleanField(
        _("Ask « Yes, I am on the plot »"),
        default=True,
        help_text=_(
            "Ask the buyer whether they are on the plot. When off, the question is skipped "
            "and the device GPS option is not offered."
        ),
    )
    allow_gps_point = models.BooleanField(
        _("Offer « Add a GPS point »"),
        default=True,
        help_text=_("Let the buyer pick the plot location on a map."),
    )
    allow_cicc_qr = models.BooleanField(
        _("Offer « Scan the CICC QR code »"),
        default=False,
        help_text=_("Let the buyer scan the QR code of a CICC plot identification card."),
    )

    class Meta:
        verbose_name = _("Options")
        verbose_name_plural = _("Options")

    def __str__(self) -> str:
        return str(_("Options"))

    @classmethod
    def load(cls) -> "GeodataOptions":
        instance = cls.objects.order_by("created_at").first()
        return instance if instance is not None else cls.objects.create()


class TraceabilityRule(BaseModel):
    """Traceability status given to a new producer transaction, by geodata source."""

    source = models.CharField(_("Geodata source"), max_length=20, choices=GeodataSource.choices, unique=True)
    traceability = models.CharField(
        _("Traceability status"),
        max_length=20,
        choices=[(item.value, item.name.capitalize()) for item in TransactionTraceability],
        help_text=_("Applies to new transactions only."),
    )
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("position",)
        verbose_name = _("Traceability rule")
        verbose_name_plural = _("Traceability rules")

    def __str__(self) -> str:
        return str(self.get_source_display())
