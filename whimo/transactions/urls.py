from django.urls import path

from whimo.transactions.views import (
    ChainCsvDownloadView,
    ChainFeatureCollectionDownloadView,
    ChainLocationBundleDownloadView,
    ConversionDetailView,
    ConversionView,
    TransactionDetailView,
    TransactionDownstreamCreateView,
    TransactionGeodataRequestView,
    TransactionGeodataUpdateView,
    TransactionListCsvDownloadView,
    TransactionListLocationBundleDownloadView,
    TransactionListLocationSummaryView,
    TransactionListView,
    TransactionNotificationResendView,
    TransactionProducerCreateView,
    TransactionStatusUpdateView,
    TransactionTraceabilityCountsView,
)

urlpatterns = [
    path("", TransactionListView.as_view(), name="transactions_list"),
    path("download/csv/", TransactionListCsvDownloadView.as_view(), name="transactions_list_csv_download"),
    path(
        "download/bundle/",
        TransactionListLocationBundleDownloadView.as_view(),
        name="transactions_list_bundle_download",
    ),
    path("download/summary/", TransactionListLocationSummaryView.as_view(), name="transactions_list_summary"),
    path("producer/", TransactionProducerCreateView.as_view(), name="transactions_producer_create"),
    path("downstream/", TransactionDownstreamCreateView.as_view(), name="transactions_downstream_create"),
    path("conversion/", ConversionView.as_view(), name="transactions_conversion"),
    path("conversion/<uuid:group_id>/", ConversionDetailView.as_view(), name="transactions_conversion_detail"),
    path("<uuid:transaction_id>/", TransactionDetailView.as_view(), name="transactions_detail"),
    path(
        "<uuid:transaction_id>/traceability-counts/",
        TransactionTraceabilityCountsView.as_view(),
        name="transactions_traceability_counts",
    ),
    path("<uuid:transaction_id>/status/", TransactionStatusUpdateView.as_view(), name="transactions_status_update"),
    path("<uuid:transaction_id>/geodata/", TransactionGeodataUpdateView.as_view(), name="transactions_geodata_update"),
    path(
        "<uuid:transaction_id>/geodata/request/",
        TransactionGeodataRequestView.as_view(),
        name="transactions_geodata_request",
    ),
    path(
        "<uuid:transaction_id>/notification/resend/",
        TransactionNotificationResendView.as_view(),
        name="transactions_notification_resend",
    ),
    path(
        "<uuid:transaction_id>/download/geojson/",
        ChainFeatureCollectionDownloadView.as_view(),
        name="transactions_chain_download",
    ),
    path(
        "<uuid:transaction_id>/download/csv/",
        ChainCsvDownloadView.as_view(),
        name="transactions_chain_csv_download",
    ),
    path(
        "<uuid:transaction_id>/download/bundle/",
        ChainLocationBundleDownloadView.as_view(),
        name="transactions_chain_bundle_download",
    ),
]
