from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from whimo.commodities.mappers.commodities import CommoditiesMapper
from whimo.db.enums import TransactionAction, TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import ConversionRecipe, Transaction
from whimo.transactions.schemas.dto import ConversionDTO, ConversionRecipeDTO, TransactionDTO
from whimo.transactions.schemas.requests import TransactionDownstreamCreateRequest, TransactionProducerCreateRequest
from whimo.users.mappers.users import UsersMapper


@dataclass(slots=True)
class TransactionsMapper:
    @staticmethod
    def to_dto(entity: Transaction, user_id: UUID, with_gadgets: bool = True) -> TransactionDTO:
        if entity.buyer_id == user_id:
            action = TransactionAction.BUYING
        elif entity.seller_id == user_id:
            action = TransactionAction.SELLING
        else:
            action = None

        commodity = CommoditiesMapper.to_dto_with_group(entity.commodity)
        seller = UsersMapper.to_dto(entity.seller, with_gadgets) if entity.seller else None
        buyer = UsersMapper.to_dto(entity.buyer, with_gadgets) if entity.buyer else None

        return TransactionDTO(
            id=entity.id,
            created_at=entity.created_at,
            # ---
            type=TransactionType(entity.type),
            status=TransactionStatus(entity.status),
            action=action,
            traceability=TransactionTraceability(entity.traceability) if entity.traceability else None,
            # ---
            location=TransactionLocation(entity.location) if entity.location else None,
            # ---
            transaction_latitude=entity.transaction_latitude,
            transaction_longitude=entity.transaction_longitude,
            # ---
            farm_latitude=entity.farm_latitude,
            farm_longitude=entity.farm_longitude,
            # ---
            commodity=commodity,
            volume=entity.volume,
            # ---
            is_buying_from_farmer=entity.is_buying_from_farmer,
            is_automatic=entity.is_automatic,
            expires_at=entity.expires_at,
            updated_at=entity.updated_at,
            # ---
            seller=seller,
            buyer=buyer,
            created_by_id=entity.created_by_id,
        )

    @staticmethod
    def to_dto_list(entities: list[Transaction], user_id: UUID) -> list[TransactionDTO]:
        return [TransactionsMapper.to_dto(entity, user_id) for entity in entities]

    @staticmethod
    def from_producer_request(
        user_id: UUID,
        traceability: TransactionTraceability,
        request: TransactionProducerCreateRequest,
    ) -> Transaction:
        return Transaction(
            type=TransactionType.PRODUCER,
            status=TransactionStatus.ACCEPTED,
            traceability=traceability,
            # ---
            location=request.location,
            # ---
            transaction_latitude=request.transaction_latitude,
            transaction_longitude=request.transaction_longitude,
            # ---
            farm_latitude=request.farm_latitude,
            farm_longitude=request.farm_longitude,
            # ---
            commodity_id=request.commodity_id,
            volume=request.volume,
            # ---
            is_buying_from_farmer=request.is_buying_from_farmer,
            is_automatic=False,
            expires_at=None,
            # ---
            seller_id=None,
            buyer_id=user_id,
            created_by_id=user_id,
        )

    @staticmethod
    def from_downstream_request(
        user_id: UUID,
        seller_id: UUID | None,
        buyer_id: UUID | None,
        request: TransactionDownstreamCreateRequest,
    ) -> Transaction:
        return Transaction(
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
            traceability=None,
            # ---
            location=None,
            # ---
            transaction_latitude=request.transaction_latitude,
            transaction_longitude=request.transaction_longitude,
            # ---
            farm_latitude=None,
            farm_longitude=None,
            # ---
            commodity_id=request.commodity_id,
            volume=request.volume,
            # ---
            is_buying_from_farmer=False,
            is_automatic=False,
            expires_at=timezone.now() + timedelta(days=settings.WHIMO_TRANSACTION_EXPIRATION_DAYS),
            # ---
            seller_id=seller_id,
            buyer_id=buyer_id,
            created_by_id=user_id,
        )

    @staticmethod
    def to_automatic_transaction(
        user_id: UUID,
        commodity_id: UUID,
        negative_volume: Decimal,
    ) -> Transaction:
        return Transaction(
            type=TransactionType.PRODUCER,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.INCOMPLETE,
            # ---
            location=None,
            # ---
            transaction_longitude=None,
            transaction_latitude=None,
            # ---
            farm_longitude=None,
            farm_latitude=None,
            # ---
            commodity_id=commodity_id,
            volume=-negative_volume,
            # ---
            is_buying_from_farmer=False,
            is_automatic=True,
            expires_at=None,
            # ---
            seller_id=None,
            buyer_id=user_id,
            created_by_id=user_id,
        )

    @staticmethod
    def to_conversion_transaction(  # noqa: PLR0913 Too many arguments in function definition
        user_id: UUID,
        commodity_id: UUID,
        volume: Decimal,
        traceability: TransactionTraceability,
        is_input: bool,
        group_id: UUID,
    ) -> Transaction:
        return Transaction(
            type=TransactionType.CONVERSION,
            status=TransactionStatus.ACCEPTED,
            traceability=traceability,
            group_id=group_id,
            # ---
            location=None,
            # ---
            transaction_longitude=None,
            transaction_latitude=None,
            # ---
            farm_longitude=None,
            farm_latitude=None,
            # ---
            commodity_id=commodity_id,
            volume=-volume if is_input else volume,
            # ---
            is_buying_from_farmer=False,
            is_automatic=False,
            expires_at=None,
            # ---
            seller_id=user_id if is_input else None,
            buyer_id=None if is_input else user_id,
            created_by_id=user_id,
        )

    @staticmethod
    def to_conversion_recipe_dto(recipe: ConversionRecipe) -> ConversionRecipeDTO:
        inputs = [
            ConversionDTO(
                id=input_item.id,
                commodity=CommoditiesMapper.to_dto_with_group(input_item.commodity),
                quantity=input_item.quantity,
            )
            for input_item in recipe.inputs_list
        ]

        outputs = [
            ConversionDTO(
                id=output_item.id,
                commodity=CommoditiesMapper.to_dto_with_group(output_item.commodity),
                quantity=output_item.quantity,
            )
            for output_item in recipe.outputs_list
        ]

        return ConversionRecipeDTO(
            id=recipe.id,
            name=_(recipe.name),
            inputs=inputs,
            outputs=outputs,
        )

    @staticmethod
    def to_conversion_recipe_dto_list(recipes: list[ConversionRecipe]) -> list[ConversionRecipeDTO]:
        return [TransactionsMapper.to_conversion_recipe_dto(recipe) for recipe in recipes]
