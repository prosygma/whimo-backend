from typing import Any

from rest_framework import views
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.commodities.mappers.balances import BalancesMapper
from whimo.commodities.mappers.commodities import CommoditiesMapper
from whimo.commodities.mappers.commodities_groups import CommoditiesGroupsMapper
from whimo.commodities.schemas.requests import BalanceListRequest, CommodityGroupListRequest, CommodityListRequest
from whimo.commodities.services.balances import BalancesService
from whimo.commodities.services.commodities import CommoditiesService
from whimo.common.schemas.base import PaginatedDataResponse


class CommoditiesListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = CommodityListRequest.parse(request, from_query_params=True)
        items, pagination = CommoditiesService.list_commodities(request=payload)

        response = CommoditiesMapper.to_dto_list_with_group(items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()


class CommoditiesGroupsListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = CommodityGroupListRequest.parse(request, from_query_params=True)
        items, pagination = CommoditiesService.list_groups(user_id=request.user.id, request=payload)

        response = CommoditiesGroupsMapper.to_dto_list_with_commodities_balances(items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()


class CommoditiesBalancesListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = BalanceListRequest.parse(request, from_query_params=True)
        items, pagination = BalancesService.list_balances(user_id=request.user.id, request=payload)

        response = BalancesMapper.to_dto_list(entities=items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()
