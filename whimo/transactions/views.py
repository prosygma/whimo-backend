from typing import Any
from uuid import UUID

from django.http import HttpResponse
from rest_framework import views
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.base import DataResponse, PaginatedDataResponse
from whimo.common.throttling import DownloadThrottle
from whimo.transactions.export.resources import TransactionUserResource
from whimo.transactions.mappers import TransactionsMapper
from whimo.transactions.schemas.dto import ChainFeatureCollectionDTO
from whimo.transactions.schemas.requests import (
    ConversionCreateRequest,
    ConversionRecipeListRequest,
    TransactionDownstreamCreateRequest,
    TransactionGeodataUpdateRequest,
    TransactionListRequest,
    TransactionProducerCreateRequest,
    TransactionStatusUpdateRequest,
)
from whimo.transactions.schemas.responses import (
    ConversionCompletedResponse,
    TransactionGeodataRequestedResponse,
    TransactionGeodataUpdatedResponse,
    TransactionNotificationResentResponse,
    TransactionStatusUpdatedResponse,
)
from whimo.transactions.services import TransactionsService


class TransactionListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = TransactionListRequest.parse(request, from_query_params=True)
        items, pagination = TransactionsService.list_transactions(user_id=request.user.id, request=payload)

        response = TransactionsMapper.to_dto_list(entities=items, user_id=request.user.id)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()


class TransactionListCsvDownloadView(views.APIView):
    throttle_classes = [DownloadThrottle]

    def get(self, request: Request, *_: Any, **__: Any) -> HttpResponse:
        payload = TransactionListRequest.parse(request, from_query_params=True)
        transactions = TransactionsService.get_list_csv_export(user_id=request.user.id, request=payload)

        resource = TransactionUserResource()
        dataset = resource.export(transactions)
        csv_data = dataset.csv

        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
        response["X-Total-Transactions"] = str(len(transactions))
        return response


class TransactionDetailView(views.APIView):
    def get(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        transaction = TransactionsService.get(user_id=request.user.id, transaction_id=transaction_id)

        response = TransactionsMapper.to_dto(entity=transaction, user_id=request.user.id)
        return DataResponse(data=response).as_response()


class TransactionTraceabilityCountsView(views.APIView):
    def get(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        counts = TransactionsService.get_seller_traceability_counts(
            user_id=request.user.id,
            transaction_id=transaction_id,
        )
        return DataResponse(data=counts).as_response()


class TransactionProducerCreateView(views.APIView):
    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = TransactionProducerCreateRequest.parse(request)
        transaction = TransactionsService.create_producer(user_id=request.user.id, request=payload)

        response = TransactionsMapper.to_dto(entity=transaction, user_id=request.user.id)
        return DataResponse(data=response).as_response()


class TransactionDownstreamCreateView(views.APIView):
    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = TransactionDownstreamCreateRequest.parse(request)
        transaction = TransactionsService.create_downstream(user_id=request.user.id, request=payload)

        response = TransactionsMapper.to_dto(entity=transaction, user_id=request.user.id)
        return DataResponse(data=response).as_response()


class ConversionView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = ConversionRecipeListRequest.parse(request, from_query_params=True)
        items, pagination = TransactionsService.list_conversion_recipes(request=payload)

        response = TransactionsMapper.to_conversion_recipe_dto_list(items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = ConversionCreateRequest.parse(request)
        TransactionsService.create_conversion(user_id=request.user.id, request=payload)
        return ConversionCompletedResponse().as_response()


class TransactionStatusUpdateView(views.APIView):
    def patch(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        payload = TransactionStatusUpdateRequest.parse(request)
        TransactionsService.update_status(user_id=request.user.id, transaction_id=transaction_id, request=payload)

        return TransactionStatusUpdatedResponse().as_response()


class TransactionGeodataUpdateView(views.APIView):
    def patch(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        payload = TransactionGeodataUpdateRequest.parse(request)
        TransactionsService.update_geodata(user_id=request.user.id, transaction_id=transaction_id, request=payload)

        return TransactionGeodataUpdatedResponse().as_response()


class TransactionGeodataRequestView(views.APIView):
    def post(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        TransactionsService.request_missing_geodata(user_id=request.user.id, transaction_id=transaction_id)
        return TransactionGeodataRequestedResponse().as_response()


class TransactionNotificationResendView(views.APIView):
    def post(self, request: Request, transaction_id: UUID, *_: Any, **__: Any) -> Response:
        TransactionsService.resend_notification(user_id=request.user.id, transaction_id=transaction_id)
        return TransactionNotificationResentResponse().as_response()


class ChainFeatureCollectionDownloadView(views.APIView):
    throttle_classes = [DownloadThrottle]

    def get(self, _: Request, transaction_id: UUID, *__: Any, **___: Any) -> Response:
        data = TransactionsService.get_chain_feature_collection(transaction_id=transaction_id)
        feature_collection, succeed_transactions, failed_transactions = data

        response = ChainFeatureCollectionDTO(
            feature_collection=feature_collection,
            succeed_transactions=succeed_transactions,
            failed_transactions=failed_transactions,
        )
        return DataResponse(data=response).as_response(by_alias=True)


class ChainCsvDownloadView(views.APIView):
    throttle_classes = [DownloadThrottle]

    def get(self, _: Request, transaction_id: UUID, *__: Any, **___: Any) -> HttpResponse:
        chain_transactions = TransactionsService.get_chain_csv_export(transaction_id)

        resource = TransactionUserResource()
        dataset = resource.export(chain_transactions)
        csv_data = dataset.csv

        response = HttpResponse(csv_data, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="transaction_{transaction_id}_chain.csv"'
        response["X-Total-Transactions"] = str(len(chain_transactions))
        return response


class ChainLocationBundleDownloadView(views.APIView):
    throttle_classes = [DownloadThrottle]

    def get(self, _: Request, transaction_id: UUID, *__: Any, **___: Any) -> HttpResponse:
        zip_data, bundle_dto = TransactionsService.get_chain_location_bundle(transaction_id=transaction_id)

        response = HttpResponse(zip_data, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="transaction_{transaction_id}_location_bundle.zip"'
        response["X-Geojson-Merged-Transactions"] = str(len(bundle_dto.geojson_merged_transactions))
        response["X-Custom-Location-File-Transactions"] = str(len(bundle_dto.custom_location_file_transactions))
        response["X-No-Location-File-Transactions"] = str(len(bundle_dto.no_location_file_transactions))
        return response
