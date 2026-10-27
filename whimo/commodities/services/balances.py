from dataclasses import dataclass
from typing import cast
from uuid import UUID

from django.db.models import Case, Exists, IntegerField, OuterRef, Q, QuerySet, Subquery, Value, When

from whimo.commodities.schemas.requests import BalanceListRequest
from whimo.common.schemas.base import Pagination
from whimo.common.utils import get_user_model, paginate_queryset
from whimo.db.enums import TransactionStatus
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Balance, ConversionInput, Transaction

User = get_user_model()

DEFAULT_BALANCE_ORDERINGS = ("-harvest_season__start_date", "commodity__name")

TRACEABILITY_RANK = Case(
    *(When(traceability=item, then=Value(rank)) for rank, item in enumerate(sorted(TransactionTraceability))),
    output_field=IntegerField(),
)


@dataclass(slots=True)
class BalancesService:
    @staticmethod
    def list_balances(user_id: UUID, request: BalanceListRequest) -> tuple[list[Balance], Pagination]:
        queryset = BalancesService._filter_balances(user_id, request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def _filter_balances(user_id: UUID, request: BalanceListRequest) -> QuerySet[Balance]:
        has_recipe_subquery = Exists(ConversionInput.objects.filter(commodity=OuterRef("commodity")))
        worst_traceability_subquery = Subquery(
            Transaction.objects.filter(
                buyer_id=OuterRef("user_id"),
                commodity_id=OuterRef("commodity_id"),
                harvest_season_id=OuterRef("harvest_season_id"),
                status=TransactionStatus.ACCEPTED,
                traceability__isnull=False,
            )
            .annotate(traceability_rank=TRACEABILITY_RANK)
            .order_by("traceability_rank")
            .values("traceability")[:1]
        )
        queryset = (
            Balance.objects.select_related("commodity__group", "commodity", "harvest_season")
            .annotate(commodity_has_recipe=has_recipe_subquery, worst_traceability=worst_traceability_subquery)
            .filter(user_id=user_id, volume__gt=0)
        )

        if search := request.search:
            queryset = queryset.filter(
                Q(commodity__name__icontains=search)
                | Q(commodity__code__icontains=search)
                | Q(commodity__name_variants__icontains=search)
            )

        if commodity_group_id := request.commodity_group_id:
            queryset = queryset.filter(commodity__group_id=commodity_group_id)

        if commodity_id := request.commodity_id:
            queryset = queryset.filter(commodity_id=commodity_id)

        if harvest_season_id := request.harvest_season_id:
            queryset = queryset.filter(harvest_season_id=harvest_season_id)

        if harvest_season_status := request.harvest_season_status:
            queryset = queryset.filter(harvest_season__status=harvest_season_status)

        orderings = request.get_orderings() or DEFAULT_BALANCE_ORDERINGS
        queryset = queryset.order_by(*orderings)

        return cast(QuerySet[Balance], queryset)
