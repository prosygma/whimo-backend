import io
import json
import logging
import zipfile
from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction as db_transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from whimo.auth.registration.services import RegistrationService
from whimo.common.schemas.base import Pagination
from whimo.common.schemas.errors import NotFound
from whimo.common.utils import get_user_model, paginate_queryset
from whimo.contrib.tasks.users import send_email, send_sms
from whimo.db.enums import GadgetType, TransactionAction, TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationType
from whimo.db.enums.transactions import TransactionLocation, TransactionTraceability
from whimo.db.models import Balance, Commodity, Gadget, Transaction
from whimo.notifications.services.notifications import NotificationsService
from whimo.notifications.services.notifications_push import NotificationsPushService
from whimo.transactions.constants import LOCATION_S3_PREFIX
from whimo.transactions.mappers import TransactionsMapper
from whimo.transactions.schemas.dto import ChainLocationBundleDTO, FeatureCollection, TraceabilityCountsDTO
from whimo.transactions.schemas.errors import (
    LocationFileDownloadError,
    LocationFileUploadError,
    RecipientConflictError,
    RecipientIsNotSpecifiedError,
)
from whimo.transactions.schemas.requests import (
    RecipientRequest,
    TransactionDownstreamCreateRequest,
    TransactionGeodataUpdateRequest,
    TransactionListRequest,
    TransactionProducerCreateRequest,
    TransactionStatusUpdateRequest,
)

User = get_user_model()
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TransactionsService:
    @staticmethod
    def get(user_id: UUID, transaction_id: UUID) -> Transaction:
        try:
            transaction = (
                TransactionsService._select_user_transaction(user_id, transaction_id)
                .select_related("commodity__group", "commodity", "buyer", "seller")
                .prefetch_related(
                    User.objects.generate_prefetch_gadgets("buyer__"),
                    User.objects.generate_prefetch_gadgets("seller__"),
                )
                .get()
            )
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        if transaction.type == TransactionType.DOWNSTREAM and not transaction.traceability:
            transaction.traceability = TransactionsService._get_downstream_traceability(
                seller_id=transaction.seller_id,
                commodity_id=transaction.commodity_id,
            )

        return transaction

    @staticmethod
    def list_transactions(user_id: UUID, request: TransactionListRequest) -> tuple[list[Transaction], Pagination]:
        queryset = TransactionsService._filter_transactions(user_id, request).prefetch_related(
            User.objects.generate_prefetch_gadgets("buyer__"),
            User.objects.generate_prefetch_gadgets("seller__"),
        )
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def get_seller_traceability_counts(user_id: UUID, transaction_id: UUID) -> TraceabilityCountsDTO:
        try:
            transaction = TransactionsService._select_user_transaction(user_id, transaction_id).get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        counts = TransactionsService._get_traceability_counts(transaction_id, transaction.commodity_id)
        return TraceabilityCountsDTO(counts=counts)

    @staticmethod
    def create_producer(user_id: UUID, request: TransactionProducerCreateRequest) -> Transaction:
        commodity = TransactionsService._get_commodity(request.commodity_id)

        balance, _ = Balance.objects.get_or_create(user_id=user_id, commodity_id=commodity.pk)

        traceability = TransactionsService._get_producer_traceability(request)
        transaction = TransactionsMapper.from_producer_request(user_id, traceability, request)

        with db_transaction.atomic():
            balance.volume += request.volume
            balance.save(update_fields=["updated_at", "volume"])
            transaction.save()

        TransactionsService._upload_location_file(transaction_id=transaction.pk, location_file=request.location_file)

        recipient, is_created = TransactionsService._get_or_create_recipient(request.recipient)
        if is_created and request.recipient:
            if email := request.recipient.email:
                TransactionsService._send_invite_email(email)
            elif phone := request.recipient.phone:
                TransactionsService._send_invite_sms(phone)

        transaction.buyer = User.objects.prefetch_gadgets().filter(pk=transaction.buyer_id).first()  # type: ignore
        return transaction

    @staticmethod
    @db_transaction.atomic
    def create_downstream(user_id: UUID, request: TransactionDownstreamCreateRequest) -> Transaction:
        if not Commodity.objects.filter(pk=request.commodity_id).exists():
            raise NotFound(errors={"commodity": [request.commodity_id]})

        recipient, is_created = TransactionsService._get_or_create_recipient(request.recipient)
        recipient_id = recipient.id if recipient else None

        if recipient_id == user_id:
            raise RecipientConflictError

        if is_created and request.recipient:
            if email := request.recipient.email:
                TransactionsService._send_invite_email(email)
            elif phone := request.recipient.phone:
                TransactionsService._send_invite_sms(phone)

        seller_id, buyer_id = TransactionsService._obtain_seller_id_and_buyer_id(
            user_id=user_id,
            recipient_id=recipient_id,
            action=request.action,
        )

        transaction = TransactionsMapper.from_downstream_request(
            user_id=user_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            request=request,
        )

        transaction.save()

        if recipient:
            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.TRANSACTION_PENDING,
                transaction=transaction,
                received_by_id=recipient_id,
                created_by_id=user_id,
            )
            NotificationsPushService.send_push([notification.id])

        if transaction.seller_id:
            transaction.seller = User.objects.prefetch_gadgets().filter(pk=transaction.seller_id).first()  # type: ignore

        if transaction.buyer_id:
            transaction.buyer = User.objects.prefetch_gadgets().filter(pk=transaction.buyer_id).first()  # type: ignore

        return transaction

    @staticmethod
    def update_status(user_id: UUID, transaction_id: UUID, request: TransactionStatusUpdateRequest) -> None:
        if request.status == TransactionStatus.ACCEPTED:
            TransactionsService._accept(user_id, transaction_id)
        else:
            TransactionsService._reject(user_id, transaction_id)

    @staticmethod
    def update_geodata(user_id: UUID, transaction_id: UUID, request: TransactionGeodataUpdateRequest) -> None:
        try:
            transaction = TransactionsService._select_user_transaction(user_id, transaction_id).get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        TransactionsService._upload_location_file(transaction_id=transaction.pk, location_file=request.location_file)
        transaction.location = request.location

        with db_transaction.atomic():
            notifications = NotificationsService.create_geodata_updated(transaction, user_id)
            NotificationsPushService.send_push([n.id for n in notifications])
            transaction.save(update_fields=["updated_at", "location"])

    @staticmethod
    def resend_notification(user_id: UUID, transaction_id: UUID) -> None:
        try:
            transaction = (
                TransactionsService._select_user_transaction(user_id, transaction_id)
                .filter(status=TransactionStatus.PENDING)
                .get()
            )
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        received_by_id = transaction.buyer_id if transaction.seller_id == user_id else transaction.seller_id
        if not received_by_id:
            raise RecipientIsNotSpecifiedError

        notification = NotificationsService.create_from_transaction(
            notification_type=NotificationType.TRANSACTION_PENDING,
            transaction=transaction,
            received_by_id=received_by_id,
            created_by_id=user_id,
        )
        NotificationsPushService.send_push([notification.id])

    @staticmethod
    def request_missing_geodata(user_id: UUID, transaction_id: UUID) -> None:
        try:
            transaction = TransactionsService._select_user_transaction(user_id, transaction_id).get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        first_transactions = TransactionsService._get_first_chain_transactions(transaction_id, transaction.commodity_id)

        for transaction in first_transactions.filter(location__isnull=True):
            if not transaction.buyer_id:
                continue

            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.GEODATA_MISSING,
                transaction=transaction,
                received_by_id=transaction.buyer_id,
                created_by_id=user_id,
            )
            NotificationsPushService.send_push([notification.id])

    @staticmethod
    def get_chain_feature_collection(transaction_id: UUID) -> tuple[FeatureCollection, list[UUID], list[UUID]]:
        try:
            transaction = Transaction.objects.get(pk=transaction_id)
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        last_transactions = TransactionsService._get_first_chain_transactions(transaction_id, transaction.commodity_id)

        data = TransactionsService._get_feature_collections(last_transactions)
        feature_collections, succeed_transactions, failed_transactions = data
        return (
            TransactionsService._merge_feature_collections(feature_collections),
            succeed_transactions,
            failed_transactions,
        )

    @staticmethod
    def get_chain_location_bundle(transaction_id: UUID) -> tuple[bytes, ChainLocationBundleDTO]:
        try:
            transaction = Transaction.objects.get(pk=transaction_id)
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        chain_transactions = TransactionsService._get_all_chain_transactions(
            transaction_id=transaction_id,
            commodity_id=transaction.commodity_id,
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            (
                geojson_merged_transactions,
                custom_location_file_transactions,
                no_location_file_transactions,
            ) = TransactionsService._process_chain_location_bundle(chain_transactions, zip_file)

        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()

        bundle_dto = ChainLocationBundleDTO(
            geojson_merged_transactions=geojson_merged_transactions,
            custom_location_file_transactions=custom_location_file_transactions,
            no_location_file_transactions=no_location_file_transactions,
        )

        return zip_data, bundle_dto

    @staticmethod
    def get_chain_csv_export(transaction_id: UUID) -> QuerySet[Transaction]:
        try:
            transaction = Transaction.objects.get(pk=transaction_id)
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        return (
            TransactionsService._get_all_chain_transactions(transaction_id, transaction.commodity_id)
            .select_related("commodity", "commodity__group", "seller", "buyer", "created_by")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
        )

    @staticmethod
    def _upload_location_file(transaction_id: UUID, location_file: InMemoryUploadedFile | None) -> None:
        if not location_file:
            return

        try:
            default_storage.save(f"{LOCATION_S3_PREFIX}/{transaction_id}", location_file)
        except Exception as exc:
            raise LocationFileUploadError from exc

    @staticmethod
    def _accept(user_id: UUID, transaction_id: UUID) -> None:
        transaction = TransactionsService._get_incoming_transaction(user_id, transaction_id, allow_created_by=False)

        seller_balance: Balance | None = None
        buyer_balance: Balance | None = None

        with db_transaction.atomic():
            if buyer_id := transaction.buyer_id:
                buyer_balance, _ = Balance.objects.select_for_update().get_or_create(
                    user_id=buyer_id,
                    commodity_id=transaction.commodity_id,
                )

            if seller_id := transaction.seller_id:
                seller_balance, _ = Balance.objects.select_for_update().get_or_create(
                    user_id=seller_id,
                    commodity_id=transaction.commodity_id,
                )

            if seller_id and seller_balance and seller_balance.volume - transaction.volume < 0:
                auto_transaction = TransactionsMapper.to_automatic_transaction(
                    user_id=seller_id,
                    commodity_id=transaction.commodity_id,
                    negative_volume=seller_balance.volume - transaction.volume,
                )
                seller_balance.volume += auto_transaction.volume
                auto_transaction.save()

            if seller_balance:
                seller_balance.volume -= transaction.volume
                seller_balance.save(update_fields=["updated_at", "volume"])

            if buyer_balance:
                buyer_balance.volume += transaction.volume
                buyer_balance.save(update_fields=["updated_at", "volume"])

            transaction.status = TransactionStatus.ACCEPTED
            transaction.expires_at = None
            transaction.traceability = TransactionsService._get_downstream_traceability(
                seller_id=seller_id,
                commodity_id=transaction.commodity_id,
            )
            transaction.save(update_fields=["updated_at", "status", "expires_at", "traceability"])

            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.TRANSACTION_ACCEPTED,
                transaction=transaction,
                received_by_id=transaction.created_by_id,
                created_by_id=user_id,
            )
            NotificationsPushService.send_push([notification.id])

    @staticmethod
    def _reject(user_id: UUID, transaction_id: UUID) -> None:
        transaction = TransactionsService._get_incoming_transaction(user_id, transaction_id, allow_created_by=True)
        transaction.status = TransactionStatus.REJECTED
        transaction.expires_at = None

        with db_transaction.atomic():
            transaction.save(update_fields=["updated_at", "status", "expires_at"])
            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.TRANSACTION_REJECTED,
                transaction=transaction,
                received_by_id=transaction.created_by_id,
                created_by_id=user_id,
            )

        NotificationsPushService.send_push([notification.id])

    @staticmethod
    def _get_commodity(commodity_id: UUID) -> Commodity:
        try:
            return Commodity.objects.get(pk=commodity_id)
        except Commodity.DoesNotExist as err:
            raise NotFound(errors={"commodity": [commodity_id]}) from err

    @staticmethod
    def _get_producer_traceability(request: TransactionProducerCreateRequest) -> TransactionTraceability:
        if request.location in {TransactionLocation.QR, TransactionLocation.GPS}:
            return TransactionTraceability.FULL

        if request.location in {TransactionLocation.MANUAL, TransactionLocation.FILE}:
            return TransactionTraceability.CONDITIONAL

        return TransactionTraceability.PARTIAL if request.is_buying_from_farmer else TransactionTraceability.INCOMPLETE

    @staticmethod
    def _get_downstream_traceability(seller_id: UUID | None, commodity_id: UUID) -> TransactionTraceability:
        seller_transactions_traceability = Transaction.objects.filter(
            buyer_id=seller_id,
            status=TransactionStatus.ACCEPTED,
            commodity_id=commodity_id,
        ).values_list("traceability", flat=True)

        if seller_transactions_traceability:
            traceability = [TransactionTraceability(trace) for trace in seller_transactions_traceability if trace]
            return min(traceability)

        return TransactionTraceability.INCOMPLETE

    @staticmethod
    def _obtain_seller_id_and_buyer_id(
        user_id: UUID,
        recipient_id: UUID | None,
        action: TransactionAction,
    ) -> tuple[UUID | None, UUID | None]:
        return (user_id, recipient_id) if action == TransactionAction.SELLING else (recipient_id, user_id)

    @staticmethod
    def _select_user_transaction(user_id: UUID, transaction_id: UUID) -> QuerySet[Transaction]:
        query = Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id), pk=transaction_id)
        return cast(QuerySet[Transaction], query)

    @staticmethod
    def _get_incoming_transaction(user_id: UUID, transaction_id: UUID, allow_created_by: bool) -> Transaction:
        queryset = Transaction.objects.select_related("commodity").filter(
            Q(buyer_id=user_id) | Q(seller_id=user_id),
            Q(expires_at__gte=timezone.now()) | Q(expires_at__isnull=True),
            pk=transaction_id,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        if not allow_created_by:
            queryset = queryset.exclude(created_by_id=user_id)

        try:
            return queryset.get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

    @staticmethod
    def _get_traceability_counts(transaction_id: UUID, commodity_id: UUID) -> dict[TransactionTraceability, int]:
        counts = {TransactionTraceability(traceability): 0 for traceability in TransactionTraceability}
        base_query = Transaction.objects.filter(commodity_id=commodity_id)

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            filters["status"] = TransactionStatus.ACCEPTED

            visited |= transactions_ids
            counts_query = transactions_query.values("traceability").annotate(count=Count("id"))
            for item in counts_query:
                if traceability := item["traceability"]:
                    counts[TransactionTraceability(traceability)] += item["count"]

            sellers_ids = transactions_query.filter(seller_id__isnull=False).values_list("seller_id", flat=True)
            transactions_ids = set(base_query.filter(buyer_id__in=sellers_ids).values_list("pk", flat=True))

        return counts

    @staticmethod
    def _get_first_chain_transactions(transaction_id: UUID, commodity_id: UUID) -> QuerySet[Transaction, Transaction]:
        first_transactions = Transaction.objects.none()
        base_query = Transaction.objects.filter(commodity_id=commodity_id)

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            filters["status"] = TransactionStatus.ACCEPTED

            visited |= transactions_ids
            first_transactions |= transactions_query.filter(seller_id__isnull=True, status=TransactionStatus.ACCEPTED)

            sellers_ids = transactions_query.filter(seller_id__isnull=False).values_list("seller_id", flat=True)
            transactions_ids = set(base_query.filter(buyer_id__in=sellers_ids).values_list("pk", flat=True))

        return cast(QuerySet[Transaction], first_transactions)

    @staticmethod
    def _get_all_chain_transactions(transaction_id: UUID, commodity_id: UUID) -> QuerySet[Transaction]:
        chain_transactions = Transaction.objects.none()
        base_query = Transaction.objects.filter(commodity_id=commodity_id)

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            chain_transactions |= transactions_query

            filters["status"] = TransactionStatus.ACCEPTED
            visited |= transactions_ids

            sellers_ids = transactions_query.filter(seller_id__isnull=False).values_list("seller_id", flat=True)
            transactions_ids = set(base_query.filter(buyer_id__in=sellers_ids).values_list("pk", flat=True))

        return cast(QuerySet[Transaction], chain_transactions)

    @staticmethod
    def _filter_transactions(user_id: UUID, request: TransactionListRequest) -> QuerySet[Transaction]:
        queryset = Transaction.objects.select_related("commodity__group", "commodity", "buyer", "seller")

        _filter = Q(buyer_id=request.buyer_id) if request.buyer_id else Q(buyer_id=user_id) | Q(seller_id=user_id)

        if search := request.search:
            _filter &= (
                Q(commodity__name__icontains=search)
                | Q(commodity__code__icontains=search)
                | Q(commodity__name_variants__icontains=search)
            )

        if status := request.status:
            _filter &= Q(status=status)

        if request.action == TransactionAction.BUYING:
            _filter &= Q(buyer_id=user_id)

        if request.action == TransactionAction.SELLING:
            _filter &= Q(seller_id=user_id)

        if created_at_from := request.created_at_from:
            _filter &= Q(created_at__gte=created_at_from)

        if created_at_to := request.created_at_to:
            _filter &= Q(created_at__lte=created_at_to)

        if commodity_group_id := request.commodity_group_id:
            _filter &= Q(commodity__group_id=commodity_group_id)

        queryset = queryset.filter(_filter)
        return cast(QuerySet[Transaction], queryset)

    @staticmethod
    def _get_or_create_recipient(request: RecipientRequest | None) -> tuple[User | None, bool]:  # type: ignore # noqa: PLR0911 too many return statements
        if not request:
            return None, False

        if username := request.name:
            try:
                user = User.objects.get(username=username)
                return user, False
            except User.DoesNotExist as err:
                raise NotFound(errors={"username": [username]}) from err

        if email := request.email:
            try:
                gadget = Gadget.objects.get(type=GadgetType.EMAIL, identifier=email)
                return gadget.user, False
            except Gadget.DoesNotExist:
                user = RegistrationService.register(request)
                return user, True

        if phone := request.phone:
            try:
                gadget = Gadget.objects.get(type=GadgetType.PHONE, identifier=phone)
                return gadget.user, False
            except Gadget.DoesNotExist:
                user = RegistrationService.register(request)
                return user, True

        return None, False

    @staticmethod
    def _get_feature_collections(
        transactions: QuerySet[Transaction],
    ) -> tuple[list[FeatureCollection], list[UUID], list[UUID]]:
        collections = []
        succeed_transactions = []
        failed_transactions = []

        for transaction in transactions:
            if transaction.location != TransactionLocation.QR:
                failed_transactions.append(transaction.pk)
                continue

            try:
                location_content = default_storage.open(f"{LOCATION_S3_PREFIX}/{transaction.id}").read().decode()
                location_data = json.loads(location_content)
            except Exception as exc:
                raise LocationFileDownloadError from exc

            try:
                collection = FeatureCollection.model_validate(location_data)
            except ValidationError as exc:
                logger.info("Transaction %s location file validation error: %s", transaction.pk, exc.json())
                failed_transactions.append(transaction.pk)
                continue

            for feature in collection.features:
                feature.properties.transaction_id = str(transaction.pk)

            collections.append(collection)
            succeed_transactions.append(transaction.pk)

        return collections, succeed_transactions, failed_transactions

    @staticmethod
    def _process_chain_location_bundle(
        transactions: QuerySet[Transaction],
        zip_file: zipfile.ZipFile,
    ) -> tuple[list[UUID], list[UUID], list[UUID]]:
        feature_collections = []
        geojson_merged_transactions = []
        custom_location_file_transactions = []
        no_location_file_transactions = []

        for tx in transactions:
            if tx.location != TransactionLocation.QR:
                no_location_file_transactions.append(tx.pk)
                continue

            custom_location_file_transactions.append(tx.pk)
            try:
                location_content = default_storage.open(f"{LOCATION_S3_PREFIX}/{tx.id}").read().decode()
            except Exception:
                no_location_file_transactions.append(tx.pk)
                continue

            try:
                location_data = json.loads(location_content)
            except json.JSONDecodeError:
                no_location_file_transactions.append(tx.pk)
                continue

            try:
                collection = FeatureCollection.model_validate(location_data)
            except ValidationError:
                no_location_file_transactions.append(tx.pk)
                continue

            for feature in collection.features:
                feature.properties.transaction_id = str(tx.pk)

            feature_collections.append(collection)
            geojson_merged_transactions.append(tx.pk)
            zip_file.writestr(f"{tx.id}.geojson", location_content)

        merged_feature_collection = TransactionsService._merge_feature_collections(feature_collections)
        merged_geojson = merged_feature_collection.model_dump_json(by_alias=True, indent=2)
        zip_file.writestr("merged.geojson", merged_geojson)

        return (
            geojson_merged_transactions,
            custom_location_file_transactions,
            no_location_file_transactions,
        )

    @staticmethod
    def _merge_feature_collections(collections: list[FeatureCollection]) -> FeatureCollection:
        features = [feature for collection in collections for feature in collection.features]
        return FeatureCollection(features=features)

    @staticmethod
    def _send_invite_email(email: str) -> None:
        send_email.delay(
            recipients=[email],
            subject=_("Welcome to WHIMO!"),
            message=_("You have been invited to Whimo!"),
        )

    @staticmethod
    def _send_invite_sms(phone: str) -> None:
        send_sms.delay(recipient=phone, message=_("You have been invited to Whimo!"))
