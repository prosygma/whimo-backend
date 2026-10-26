import io
import json
import logging
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction as db_transaction
from django.db.models import Q, QuerySet
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError

from whimo.auth.registration.services import RegistrationService
from whimo.common.schemas.base import Pagination
from whimo.common.schemas.errors import NotFound
from whimo.common.test_mode import is_test_mode
from whimo.common.utils import get_user_model, paginate_queryset
from whimo.contrib.tasks.users import send_email, send_sms
from whimo.db.enums import GadgetType, HarvestSeasonStatus, TransactionAction, TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationType
from whimo.db.enums.transactions import TransactionLocation, TransactionTraceability
from whimo.db.models import Balance, Commodity, ConversionRecipe, HarvestSeason, HarvestSeasonCommodity, Transaction
from whimo.db.storages import TransactionsStorage, UsersStorage
from whimo.notifications.services.notifications import NotificationsService
from whimo.notifications.services.notifications_push import NotificationsPushService
from whimo.transactions.constants import CHAIN_TIER_FIELD, LOCATION_S3_PREFIX
from whimo.transactions.mappers import TransactionsMapper
from whimo.transactions.schemas.dto import (
    ChainLocationBundleDTO,
    Feature,
    FeatureCollection,
    FeatureProperties,
    LocationSummaryDTO,
    PointGeometry,
    TraceabilityCountsDTO,
)
from whimo.transactions.schemas.errors import (
    ActiveHarvestSeasonNotConfiguredError,
    AtLeastOneInputRequiredError,
    CommodityArchivedError,
    CommodityNotInHarvestSeasonError,
    InsufficientHarvestSeasonBalanceError,
    InvalidRecipeOverrideError,
    LocationFileDownloadError,
    LocationFileUploadError,
    RecipeNotFoundError,
    RecipientConflictError,
    RecipientIsNotSpecifiedError,
    RecipientNotFoundError,
)
from whimo.transactions.schemas.requests import (
    ConversionCreateRequest,
    ConversionRecipeListRequest,
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
        transaction = TransactionsStorage.get_user_transaction_with_relations(user_id, transaction_id)

        if transaction.type == TransactionType.DOWNSTREAM and not transaction.traceability:
            transaction.traceability = TransactionsStorage.get_downstream_traceability(
                seller_id=transaction.seller_id,
                commodity_id=transaction.commodity_id,
                harvest_season_id=transaction.harvest_season_id,
            )

        return transaction

    @staticmethod
    def list_transactions(user_id: UUID, request: TransactionListRequest) -> tuple[list[Transaction], Pagination]:
        queryset = TransactionsStorage.filter_transactions(user_id, request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def get_seller_traceability_counts(user_id: UUID, transaction_id: UUID) -> TraceabilityCountsDTO:
        if not TransactionsStorage.select_user_transaction(user_id, transaction_id).exists():
            raise NotFound(errors={"transaction": [transaction_id]})

        counts = TransactionsStorage.get_traceability_counts(transaction_id)
        return TraceabilityCountsDTO(counts=counts)

    @staticmethod
    def create_producer(user_id: UUID, request: TransactionProducerCreateRequest) -> Transaction:
        try:
            commodity = Commodity.objects.get(pk=request.commodity_id)
        except Commodity.DoesNotExist as err:
            raise NotFound(errors={"commodity": [request.commodity_id]}) from err

        if commodity.is_archived:
            raise CommodityArchivedError(commodity.pk)

        harvest_season_id = TransactionsService._resolve_harvest_season_id(commodity.pk, request.harvest_season_id)
        balance, _ = Balance.objects.get_or_create(
            user_id=user_id,
            commodity_id=commodity.pk,
            harvest_season_id=harvest_season_id,
        )

        traceability = TransactionsService._get_producer_traceability(request)
        transaction = TransactionsMapper.from_producer_request(user_id, traceability, harvest_season_id, request)

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
        try:
            commodity = Commodity.objects.get(pk=request.commodity_id)
        except Commodity.DoesNotExist as err:
            raise NotFound(errors={"commodity": [request.commodity_id]}) from err

        if commodity.is_archived:
            raise CommodityArchivedError(commodity.pk)

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

        TransactionsService._validate_harvest_season_covers(request.harvest_season_id, [request.commodity_id])

        transaction = TransactionsMapper.from_downstream_request(
            user_id=user_id,
            seller_id=seller_id,
            buyer_id=buyer_id,
            harvest_season_id=request.harvest_season_id,
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
    def update_status(
        user_id: UUID,
        transaction_id: UUID,
        request: TransactionStatusUpdateRequest,
    ) -> tuple[Transaction, Transaction | None]:
        if request.status == TransactionStatus.ACCEPTED:
            return TransactionsService._accept(user_id, transaction_id)

        return TransactionsService._reject(user_id, transaction_id), None

    @staticmethod
    def update_geodata(user_id: UUID, transaction_id: UUID, request: TransactionGeodataUpdateRequest) -> None:
        try:
            transaction = TransactionsStorage.select_user_transaction(user_id, transaction_id).get()
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
                TransactionsStorage.select_user_transaction(user_id, transaction_id)
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
            transaction = TransactionsStorage.select_user_transaction(user_id, transaction_id).get()
        except Transaction.DoesNotExist as err:
            raise NotFound(errors={"transaction": [transaction_id]}) from err

        first_transactions = TransactionsStorage.get_first_chain_transactions(transaction_id)

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
    def check_chain_access(user_id: UUID, transaction_id: UUID) -> None:
        # A chain carries the farm coordinates and the ids of every supplier behind it,
        # so over the API only the two sides of its root transaction may read it. The
        # admin actions call the chain services directly and stay outside this rule.
        if not TransactionsStorage.select_user_transaction(user_id, transaction_id).exists():
            raise NotFound(errors={"transaction": [transaction_id]})

    @staticmethod
    def get_chain_feature_collection(transaction_id: UUID) -> tuple[FeatureCollection, list[UUID], list[UUID]]:
        if not Transaction.objects.filter(pk=transaction_id).exists():
            raise NotFound(errors={"transaction": [transaction_id]})

        first_transactions = TransactionsStorage.get_first_chain_transactions(transaction_id)

        data = TransactionsService._get_feature_collections(first_transactions)
        feature_collections, succeed_transactions, failed_transactions = data
        return (
            TransactionsService._merge_feature_collections(feature_collections),
            succeed_transactions,
            failed_transactions,
        )

    @staticmethod
    def get_chain_location_bundle(transaction_id: UUID) -> tuple[bytes, ChainLocationBundleDTO]:
        if not Transaction.objects.filter(pk=transaction_id).exists():
            raise NotFound(errors={"transaction": [transaction_id]})

        farm_transactions = list(TransactionsStorage.get_first_chain_transactions(transaction_id))
        return TransactionsService._build_location_bundle(farm_transactions)

    @staticmethod
    def get_list_location_bundle(
        user_id: UUID, request: TransactionListRequest
    ) -> tuple[bytes, ChainLocationBundleDTO]:
        farm_transactions = TransactionsStorage.get_filtered_chains_farms(user_id, request)
        return TransactionsService._build_location_bundle(farm_transactions)

    @staticmethod
    def get_list_location_summary(user_id: UUID, request: TransactionListRequest) -> LocationSummaryDTO:
        roots = TransactionsStorage.filter_chain_roots(user_id, request)
        farm_transactions = TransactionsStorage.get_chains_farms(roots)

        bundle_dto = TransactionsService._classify_farms(farm_transactions)
        traders = {root.buyer_id for root in roots} | {root.seller_id for root in roots}

        return LocationSummaryDTO(
            full_traceability_farms=len(bundle_dto.geojson_merged_transactions),
            manually_added_farms=len(bundle_dto.custom_location_file_transactions),
            farms_without_geolocation=len(bundle_dto.no_location_file_transactions),
            traders=len(traders - {user_id, None}),
        )

    @staticmethod
    def get_chain_csv_export(transaction_id: UUID) -> QuerySet[Transaction]:
        if not Transaction.objects.filter(pk=transaction_id).exists():
            raise NotFound(errors={"transaction": [transaction_id]})

        return (
            TransactionsStorage.get_chain_transactions(transaction_id)
            .select_related("commodity", "commodity__group", "harvest_season", "seller", "buyer", "created_by")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
        )

    @staticmethod
    def get_list_csv_export(
        user_id: UUID, request: TransactionListRequest
    ) -> QuerySet[Transaction] | list[Transaction]:
        queryset = (
            TransactionsStorage.filter_transactions(user_id, request)
            .select_related("commodity", "commodity__group", "harvest_season", "seller", "buyer", "created_by")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
        )
        if not request.include_chain:
            return queryset

        roots = TransactionsStorage.filter_chain_roots(user_id, request)
        tiers = {
            transaction.pk: getattr(transaction, CHAIN_TIER_FIELD)
            for transaction in TransactionsStorage.get_chains_transactions(roots)
        }

        # The traversal reads the rows it walks without their relations; the export
        # needs them, so the whole chain is read once more with everything attached.
        # It cannot go through the filtered queryset: a supplier transaction the user
        # is not a party to would fall out of it.
        transactions = list(
            Transaction.objects.select_related(
                "commodity",
                "commodity__group",
                "harvest_season",
                "seller",
                "buyer",
                "created_by",
            )
            .prefetch_related("seller__gadgets", "buyer__gadgets")
            .filter(pk__in=tiers),
        )
        for transaction in transactions:
            setattr(transaction, CHAIN_TIER_FIELD, tiers[transaction.pk])

        return transactions

    @staticmethod
    def create_conversion(user_id: UUID, request: ConversionCreateRequest) -> list[Transaction]:
        try:
            recipe = ConversionRecipe.objects.prefetch_conversion_data().get(id=request.recipe_id)
        except ConversionRecipe.DoesNotExist as err:
            raise RecipeNotFoundError from err

        TransactionsService._validate_recipe_commodities_active(recipe)

        recipe_input_ids = {inp.commodity_id for inp in recipe.inputs_list}
        recipe_output_ids = {out.commodity_id for out in recipe.outputs_list}

        if request.input_overrides:
            override_input_ids = {item.commodity_id for item in request.input_overrides}
            if not override_input_ids.issubset(recipe_input_ids):
                raise InvalidRecipeOverrideError

        if request.output_overrides:
            override_output_ids = {item.commodity_id for item in request.output_overrides}
            if not override_output_ids.issubset(recipe_output_ids):
                raise InvalidRecipeOverrideError

        input_override_map = {item.commodity_id: item.quantity for item in request.input_overrides or []}
        output_override_map = {item.commodity_id: item.quantity for item in request.output_overrides or []}

        input_commodities = {
            inp.commodity_id: input_override_map.get(inp.commodity_id, inp.quantity) for inp in recipe.inputs_list
        }

        if all(qty == 0 for qty in input_commodities.values()):
            raise AtLeastOneInputRequiredError

        output_commodities = {
            out.commodity_id: output_override_map.get(out.commodity_id, out.quantity) for out in recipe.outputs_list
        }

        input_commodities = {k: v for k, v in input_commodities.items() if v > 0}
        output_commodities = {k: v for k, v in output_commodities.items() if v > 0}

        TransactionsService._validate_harvest_season_covers(
            request.harvest_season_id,
            list(input_commodities.keys()) + list(output_commodities.keys()),
        )

        traceability = TransactionsStorage.get_conversion_traceability(
            user_id=user_id,
            input_commodity_ids=list(input_commodities.keys()),
            harvest_season_id=request.harvest_season_id,
        )

        group_id = uuid4()

        with db_transaction.atomic():
            input_balances_to_update, input_transactions = TransactionsService._process_conversion_inputs(
                user_id=user_id,
                input_commodities=input_commodities,
                harvest_season_id=request.harvest_season_id,
                traceability=traceability,
                group_id=group_id,
            )

            output_balances_to_update, output_balances_to_create, output_transactions = (
                TransactionsService._process_conversion_outputs(
                    user_id=user_id,
                    output_commodities=output_commodities,
                    harvest_season_id=request.harvest_season_id,
                    traceability=traceability,
                    group_id=group_id,
                )
            )

            all_balances_to_update = input_balances_to_update + output_balances_to_update
            all_transactions = input_transactions + output_transactions

            if all_balances_to_update:
                Balance.objects.bulk_update(all_balances_to_update, ["volume", "updated_at"])

            if output_balances_to_create:
                Balance.objects.bulk_create(output_balances_to_create)

            Transaction.objects.bulk_create(all_transactions)

            return all_transactions

    @staticmethod
    def _upload_location_file(transaction_id: UUID, location_file: InMemoryUploadedFile | None) -> None:
        if not location_file:
            return

        try:
            default_storage.save(f"{LOCATION_S3_PREFIX}/{transaction_id}", location_file)
        except Exception as exc:
            raise LocationFileUploadError from exc

    @staticmethod
    def _accept(user_id: UUID, transaction_id: UUID) -> tuple[Transaction, Transaction | None]:
        transaction = TransactionsStorage.get_incoming_transaction(user_id, transaction_id, allow_created_by=False)

        seller_balance: Balance | None = None
        buyer_balance: Balance | None = None
        auto_transaction: Transaction | None = None

        harvest_season_id = transaction.harvest_season_id

        with db_transaction.atomic():
            if buyer_id := transaction.buyer_id:
                buyer_balance, _ = Balance.objects.select_for_update().get_or_create(
                    user_id=buyer_id,
                    commodity_id=transaction.commodity_id,
                    harvest_season_id=harvest_season_id,
                )

            if seller_id := transaction.seller_id:
                seller_balance, _ = Balance.objects.select_for_update().get_or_create(
                    user_id=seller_id,
                    commodity_id=transaction.commodity_id,
                    harvest_season_id=harvest_season_id,
                )

            if seller_id and seller_balance and seller_balance.volume - transaction.volume < 0:
                if transaction.harvest_season.status != HarvestSeasonStatus.ACTIVE:
                    raise InsufficientHarvestSeasonBalanceError(
                        harvest_season_id=harvest_season_id,
                        available_volume=seller_balance.volume,
                        requested_volume=transaction.volume,
                    )

                auto_transaction = TransactionsMapper.to_automatic_transaction(
                    user_id=seller_id,
                    commodity_id=transaction.commodity_id,
                    harvest_season_id=harvest_season_id,
                    negative_volume=seller_balance.volume - transaction.volume,
                )
                seller_balance.volume += auto_transaction.volume
                auto_transaction.save()
                auto_transaction = TransactionsStorage.get_transaction_with_relations(auto_transaction.pk)

            if seller_balance:
                seller_balance.volume -= transaction.volume
                seller_balance.save(update_fields=["updated_at", "volume"])

            if buyer_balance:
                buyer_balance.volume += transaction.volume
                buyer_balance.save(update_fields=["updated_at", "volume"])

            transaction.status = TransactionStatus.ACCEPTED
            transaction.expires_at = None
            transaction.traceability = TransactionsStorage.get_downstream_traceability(
                seller_id=seller_id,
                commodity_id=transaction.commodity_id,
                harvest_season_id=harvest_season_id,
            )
            transaction.save(update_fields=["updated_at", "status", "expires_at", "traceability"])

            notification = NotificationsService.create_from_transaction(
                notification_type=NotificationType.TRANSACTION_ACCEPTED,
                transaction=transaction,
                received_by_id=transaction.created_by_id,
                created_by_id=user_id,
            )
            NotificationsPushService.send_push([notification.id])

        return transaction, auto_transaction

    @staticmethod
    def _reject(user_id: UUID, transaction_id: UUID) -> Transaction:
        transaction = TransactionsStorage.get_incoming_transaction(user_id, transaction_id, allow_created_by=True)
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

        return transaction

    @staticmethod
    def _get_producer_traceability(request: TransactionProducerCreateRequest) -> TransactionTraceability:
        if request.location in {TransactionLocation.QR, TransactionLocation.GPS}:
            return TransactionTraceability.FULL

        if request.location in {TransactionLocation.MANUAL, TransactionLocation.FILE}:
            return TransactionTraceability.CONDITIONAL

        return TransactionTraceability.PARTIAL if request.is_buying_from_farmer else TransactionTraceability.INCOMPLETE

    @staticmethod
    def _obtain_seller_id_and_buyer_id(
        user_id: UUID,
        recipient_id: UUID | None,
        action: TransactionAction,
    ) -> tuple[UUID | None, UUID | None]:
        return (user_id, recipient_id) if action == TransactionAction.SELLING else (recipient_id, user_id)

    @staticmethod
    def _get_or_create_recipient(request: RecipientRequest | None) -> tuple[User | None, bool]:  # type: ignore # noqa: PLR0911 too many return statements
        if not request:
            return None, False

        if username := request.name:
            # A deleted account keeps its username while its gadgets are gone, so the
            # User ID is the one way a transaction could still reach one.
            try:
                user = User.objects.get(username=username, is_deleted=False)
                return user, False
            except User.DoesNotExist as err:
                raise RecipientNotFoundError(errors={"recipient": [username]}) from err

        if email := request.email:
            existing_user = UsersStorage.get_user_by_gadget(GadgetType.EMAIL, email)
            if existing_user:
                return existing_user, False
            new_user = RegistrationService.register(request)
            return new_user, True

        if phone := request.phone:
            existing_user = UsersStorage.get_user_by_gadget(GadgetType.PHONE, phone)
            if existing_user:
                return existing_user, False
            new_user = RegistrationService.register(request)
            return new_user, True

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
                collection = FeatureCollection.from_geojson(location_data)
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
    def _build_location_bundle(farm_transactions: list[Transaction]) -> tuple[bytes, ChainLocationBundleDTO]:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            TransactionsService._write_farm_locations(farm_transactions, zip_file)

        zip_buffer.seek(0)
        return zip_buffer.getvalue(), TransactionsService._classify_farms(farm_transactions)

    @staticmethod
    def _classify_farms(farm_transactions: list[Transaction]) -> ChainLocationBundleDTO:
        bundle_dto = ChainLocationBundleDTO(
            geojson_merged_transactions=[],
            custom_location_file_transactions=[],
            no_location_file_transactions=[],
        )
        buckets = {
            TransactionLocation.QR: bundle_dto.geojson_merged_transactions,
            TransactionLocation.GPS: bundle_dto.geojson_merged_transactions,
            TransactionLocation.FILE: bundle_dto.custom_location_file_transactions,
            TransactionLocation.MANUAL: bundle_dto.custom_location_file_transactions,
        }

        for farm in farm_transactions:
            if not farm.location:
                bundle_dto.no_location_file_transactions.append(farm.pk)
                continue

            buckets[TransactionLocation(farm.location)].append(farm.pk)

        return bundle_dto

    @staticmethod
    def _write_farm_locations(farm_transactions: list[Transaction], zip_file: zipfile.ZipFile) -> None:
        features = []
        for farm in farm_transactions:
            if farm.location in {TransactionLocation.QR, TransactionLocation.FILE}:
                if location_file := TransactionsService._read_location_file(farm.pk):
                    features += TransactionsService._add_location_file(farm, location_file, zip_file)
                continue

            if farm.location and (point := TransactionsService._farm_point(farm)):
                features.append(point)

        merged = FeatureCollection(features=features)
        zip_file.writestr("merged.geojson", merged.model_dump_json(by_alias=True, indent=2))

    @staticmethod
    def _read_location_file(transaction_id: UUID) -> bytes | None:
        try:
            return cast(bytes, default_storage.open(f"{LOCATION_S3_PREFIX}/{transaction_id}").read())
        except Exception:
            logger.warning("Transaction %s location file is missing", transaction_id)
            return None

    @staticmethod
    def _add_location_file(farm: Transaction, location_file: bytes, zip_file: zipfile.ZipFile) -> list[Feature]:
        # An uploaded file is stored under the transaction id alone, without an
        # extension, and its format is not ours to parse - it goes into the zip as is.
        if farm.location == TransactionLocation.FILE:
            zip_file.writestr(str(farm.pk), location_file)
            return []

        try:
            collection = FeatureCollection.from_geojson(json.loads(location_file.decode()))
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError):
            logger.warning("Transaction %s location file is not a valid geojson", farm.pk)
            return []

        for feature in collection.features:
            feature.properties.transaction_id = str(farm.pk)

        zip_file.writestr(f"{farm.pk}.geojson", location_file)
        return collection.features

    @staticmethod
    def _farm_point(farm: Transaction) -> Feature | None:
        latitude = farm.farm_latitude if farm.farm_latitude is not None else farm.transaction_latitude
        longitude = farm.farm_longitude if farm.farm_longitude is not None else farm.transaction_longitude
        if latitude is None or longitude is None:
            logger.warning("Transaction %s has no coordinates to place on the map", farm.pk)
            return None

        return Feature(
            properties=FeatureProperties(TransactionId=str(farm.pk)),
            geometry=PointGeometry(coordinates=[longitude, latitude]),
        )

    @staticmethod
    def _merge_feature_collections(collections: list[FeatureCollection]) -> FeatureCollection:
        features = [feature for collection in collections for feature in collection.features]
        return FeatureCollection(features=features)

    @staticmethod
    def _send_invite_email(email: str) -> None:
        if is_test_mode():
            return

        send_email.delay(
            recipients=[email],
            subject=_("Welcome to WHIMO!"),
            message=_("You have been invited to Whimo!"),
        )

    @staticmethod
    def _send_invite_sms(phone: str) -> None:
        if is_test_mode():
            return

        send_sms.delay(recipient=phone, message=_("You have been invited to Whimo!"))

    @staticmethod
    def _validate_conversion_commodities(commodity_ids: set[UUID]) -> None:
        existing_count = Commodity.objects.filter(id__in=commodity_ids).count()
        if existing_count != len(commodity_ids):
            raise NotFound(errors={"commodities": ["One or more commodities do not exist"]})

    @staticmethod
    def _validate_recipe_commodities_active(recipe: ConversionRecipe) -> None:
        commodities = [item.commodity for item in recipe.inputs_list] + [item.commodity for item in recipe.outputs_list]
        for commodity in commodities:
            if commodity.is_archived:
                raise CommodityArchivedError(commodity.pk)

    @staticmethod
    def _resolve_harvest_season_id(commodity_id: UUID, harvest_season_id: UUID | None) -> UUID:
        if not harvest_season_id:
            return TransactionsService._get_active_harvest_season_id(commodity_id)

        TransactionsService._validate_harvest_season_covers(harvest_season_id, [commodity_id])
        return harvest_season_id

    @staticmethod
    def _validate_harvest_season_covers(harvest_season_id: UUID, commodity_ids: list[UUID]) -> None:
        if not HarvestSeason.objects.filter(pk=harvest_season_id).exists():
            raise NotFound(errors={"harvest_season": [harvest_season_id]})

        covered = set(
            HarvestSeasonCommodity.objects.filter(
                harvest_season_id=harvest_season_id,
                commodity_id__in=commodity_ids,
            ).values_list("commodity_id", flat=True)
        )

        for commodity_id in commodity_ids:
            if commodity_id not in covered:
                raise CommodityNotInHarvestSeasonError(harvest_season_id, commodity_id)

    @staticmethod
    def _get_active_harvest_season_id(commodity_id: UUID) -> UUID:
        harvest_season_id = (
            HarvestSeason.objects.filter(
                harvest_season_commodities__commodity_id=commodity_id,
                status=HarvestSeasonStatus.ACTIVE,
            )
            .values_list("pk", flat=True)
            .first()
        )
        if not harvest_season_id:
            raise ActiveHarvestSeasonNotConfiguredError

        return cast(UUID, harvest_season_id)

    @staticmethod
    def _process_conversion_inputs(
        user_id: UUID,
        input_commodities: dict[UUID, Decimal],
        harvest_season_id: UUID,
        traceability: TransactionTraceability,
        group_id: UUID,
    ) -> tuple[list[Balance], list[Transaction]]:
        existing_input_balances = {
            balance.commodity_id: balance
            for balance in Balance.objects.select_for_update().filter(
                user_id=user_id,
                commodity_id__in=input_commodities.keys(),
                harvest_season_id=harvest_season_id,
            )
        }

        for commodity_id, required_volume in input_commodities.items():
            balance = existing_input_balances.get(commodity_id)
            if not balance or balance.volume < required_volume:
                raise InsufficientHarvestSeasonBalanceError(
                    harvest_season_id=harvest_season_id,
                    available_volume=balance.volume if balance else Decimal(0),
                    requested_volume=required_volume,
                )

        balances_to_update = []
        transactions = []

        for commodity_id, volume in input_commodities.items():
            balance = existing_input_balances[commodity_id]
            balance.volume -= volume
            balances_to_update.append(balance)

            transaction = TransactionsMapper.to_conversion_transaction(
                user_id=user_id,
                commodity_id=commodity_id,
                harvest_season_id=harvest_season_id,
                volume=volume,
                traceability=traceability,
                is_input=True,
                group_id=group_id,
            )
            transactions.append(transaction)

        return balances_to_update, transactions

    @staticmethod
    def _process_conversion_outputs(
        user_id: UUID,
        output_commodities: dict[UUID, Decimal],
        harvest_season_id: UUID,
        traceability: TransactionTraceability,
        group_id: UUID,
    ) -> tuple[list[Balance], list[Balance], list[Transaction]]:
        existing_output_balances = {
            balance.commodity_id: balance
            for balance in Balance.objects.select_for_update().filter(
                user_id=user_id,
                commodity_id__in=output_commodities.keys(),
                harvest_season_id=harvest_season_id,
            )
        }

        balances_to_update = []
        balances_to_create = []
        transactions = []

        for commodity_id, volume in output_commodities.items():
            balance = existing_output_balances.get(commodity_id)
            if balance:
                balance.volume += volume
                balances_to_update.append(balance)
            else:
                balance = Balance(
                    user_id=user_id,
                    commodity_id=commodity_id,
                    harvest_season_id=harvest_season_id,
                    volume=volume,
                )
                balances_to_create.append(balance)

            transaction = TransactionsMapper.to_conversion_transaction(
                user_id=user_id,
                commodity_id=commodity_id,
                harvest_season_id=harvest_season_id,
                volume=volume,
                traceability=traceability,
                is_input=False,
                group_id=group_id,
            )
            transactions.append(transaction)

        return balances_to_update, balances_to_create, transactions

    @staticmethod
    def list_conversion_recipes(request: ConversionRecipeListRequest) -> tuple[list[ConversionRecipe], Pagination]:
        queryset = TransactionsService._filter_conversion_recipes(request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def _filter_conversion_recipes(request: ConversionRecipeListRequest) -> QuerySet[ConversionRecipe]:
        queryset = (
            ConversionRecipe.objects.prefetch_conversion_data()
            .exclude(inputs__commodity__is_archived=True)
            .exclude(outputs__commodity__is_archived=True)
        )

        if search := request.search:
            queryset = queryset.filter(Q(name__icontains=search))

        if commodity_id := request.commodity_id:
            queryset = queryset.filter(inputs__commodity_id=commodity_id).distinct()

        return cast(QuerySet[ConversionRecipe], queryset)
