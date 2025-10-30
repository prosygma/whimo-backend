from dataclasses import dataclass
from typing import cast
from uuid import UUID

from django.db.models import Q, QuerySet

from whimo.commodities.schemas.requests import BalanceListRequest
from whimo.common.schemas.base import Pagination
from whimo.common.utils import get_user_model, paginate_queryset
from whimo.db.models import Balance

User = get_user_model()


@dataclass(slots=True)
class BalancesService:
    @staticmethod
    def list_balances(user_id: UUID, request: BalanceListRequest) -> tuple[list[Balance], Pagination]:
        queryset = BalancesService._filter_balances(user_id, request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def _filter_balances(user_id: UUID, request: BalanceListRequest) -> QuerySet[Balance]:
        queryset = Balance.objects.select_related("commodity__group", "commodity").filter(user_id=user_id)

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

        return cast(QuerySet[Balance], queryset)
