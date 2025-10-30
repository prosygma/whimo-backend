from dataclasses import dataclass
from typing import cast
from uuid import UUID

from django.db.models import Prefetch, Q, QuerySet

from whimo.commodities.schemas.requests import CommodityGroupListRequest, CommodityListRequest
from whimo.common.schemas.base import Pagination
from whimo.common.utils import paginate_queryset
from whimo.db.models import Commodity, CommodityGroup


@dataclass(slots=True)
class CommoditiesService:
    @staticmethod
    def list_commodities(request: CommodityListRequest) -> tuple[list[Commodity], Pagination]:
        queryset = CommoditiesService._filter_commodities(request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def list_groups(user_id: UUID, request: CommodityGroupListRequest) -> tuple[list[CommodityGroup], Pagination]:
        queryset = CommoditiesService._filter_commodities_groups(user_id, request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def _filter_commodities(params: CommodityListRequest) -> QuerySet[Commodity]:
        queryset = Commodity.objects.select_related("group")

        if search := params.search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search) | Q(name_variants__icontains=search)
            )

        if group_id := params.group_id:
            queryset = queryset.filter(group_id=group_id)

        return cast(QuerySet[Commodity], queryset)

    @staticmethod
    def _filter_commodities_groups(user_id: UUID, params: CommodityGroupListRequest) -> QuerySet[CommodityGroup]:
        commodities_with_balances = Commodity.objects.annotate_balances(user_id)
        queryset = CommodityGroup.objects.prefetch_related(Prefetch("commodities", queryset=commodities_with_balances))

        if search := params.search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(name_variants__icontains=search))

        return cast(QuerySet[CommodityGroup], queryset)
