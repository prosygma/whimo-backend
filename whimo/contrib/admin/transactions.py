from uuid import UUID

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.safestring import SafeString
from django.utils.translation import gettext_lazy as _
from import_export.admin import ExportActionMixin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import AllValuesCheckboxFilter, AutocompleteSelectFilter, RangeDateFilter
from unfold.contrib.import_export.forms import ExportForm
from unfold.decorators import action, display

from whimo.contrib.utils import ReadOnlyAdminMixin, change_link_with_icon, colored_text, text_with_icon
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Transaction
from whimo.db.storages import TransactionsStorage
from whimo.transactions.export.resources import TransactionAdminResource
from whimo.transactions.services import TransactionsService


@admin.register(Transaction)
class TransactionAdmin(ReadOnlyAdminMixin, ModelAdmin, ExportActionMixin, SimpleHistoryAdmin):
    resource_classes = [TransactionAdminResource]
    export_form_class = ExportForm  # type: ignore
    actions_detail = ("download_chain", "download_geojson")  # type: ignore

    list_display = (
        "short_id",
        "type_labeled",
        "status_labeled",
        "traceability_labeled",
        "commodity_link",
        "seller_link",
        "buyer_link",
        "created_by_link",
        "created_at",
    )
    list_filter = (
        ("commodity", AutocompleteSelectFilter),
        ("seller", AutocompleteSelectFilter),
        ("buyer", AutocompleteSelectFilter),
        ("created_by", AutocompleteSelectFilter),
        ("traceability", AllValuesCheckboxFilter),
        ("status", AllValuesCheckboxFilter),
        ("location", AllValuesCheckboxFilter),
        ("created_at", RangeDateFilter),
    )
    list_filter_submit = True
    list_select_related = ("commodity", "seller", "buyer", "created_by")
    search_fields = ("commodity__name", "commodity__code", "seller__username", "buyer__username")
    ordering = ("-created_at",)

    fieldsets = (
        (_("Transaction"), {"fields": ("status", "traceability", "seller", "buyer", "created_by")}),
        (_("Commodity"), {"fields": ("commodity", "volume")}),
        (_("Location"), {"fields": ("location", "transaction_latitude", "transaction_longitude")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("commodity", "seller", "buyer")

    def get_export_queryset(self, request: HttpRequest) -> QuerySet[Transaction]:
        return (
            super()
            .get_export_queryset(request)
            .select_related("commodity", "commodity__group", "seller", "buyer", "created_by")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
        )

    @action(description="Download chain")
    def download_chain(self, request: HttpRequest, object_id: str) -> HttpResponse:
        transaction = Transaction.objects.get(pk=object_id)
        chain_transactions = (
            TransactionsStorage.get_chain_transactions(transaction.id)
            .select_related("commodity", "commodity__group", "seller", "buyer", "created_by")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
        )
        return self.export_admin_action(request=request, queryset=chain_transactions)

    @action(description="Download GeoJSON")
    def download_geojson(self, request: HttpRequest, object_id: UUID) -> HttpResponse:
        transaction = Transaction.objects.get(pk=object_id)

        data = TransactionsService.get_chain_feature_collection(transaction_id=object_id)
        feature_collection, succeed_transactions, failed_transactions = data

        if succeed_transactions:
            messages.success(
                request,
                f"Successfully processed {len(succeed_transactions)} transactions:"
                f"{'\n'.join([str(trx) for trx in succeed_transactions])}",
            )

        if failed_transactions:
            messages.warning(
                request,
                f"Failed to process {len(failed_transactions)} transactions:"
                f"{'\n'.join([str(trx) for trx in failed_transactions])}",
            )

        geojson_data = feature_collection.model_dump_json(by_alias=True, indent=2)

        response = HttpResponse(geojson_data, content_type="application/json")
        response["Content-Disposition"] = f'attachment; filename="transaction_{transaction.short_id}_farms.json"'
        return response

    @display(description="ID", ordering="id")
    def short_id(self, obj: Transaction) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(description="Commodity", ordering="commodity__name", label=True)
    def commodity_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="Seller", ordering="seller__id", label=True)
    def seller_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.seller)

    @display(description="Buyer", ordering="buyer__id", label=True)
    def buyer_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.buyer)

    @display(description="Created By", ordering="created_by__id", label=True)
    def created_by_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.created_by)

    @display(description="Type", ordering="type", label=True)
    def type_labeled(self, obj: Transaction) -> str:
        icon = "potted_plant" if obj.type == TransactionType.PRODUCER else "storefront"
        return text_with_icon(obj.type, icon=icon)

    @display(
        description="Status",
        ordering="status",
        label={
            TransactionStatus.PENDING: "info",
            TransactionStatus.ACCEPTED: "success",
            TransactionStatus.REJECTED: "danger",
            TransactionStatus.NO_RESPONSE: "warning",
        },
    )
    def status_labeled(self, obj: Transaction) -> str:
        return obj.status

    @display(
        description="Traceability",
        ordering="traceability",
        label={
            TransactionTraceability.FULL: "success",
            TransactionTraceability.CONDITIONAL: "info",
            TransactionTraceability.PARTIAL: "warning",
            TransactionTraceability.INCOMPLETE: "danger",
        },
    )
    def traceability_labeled(self, obj: Transaction) -> str | None:
        return obj.traceability
