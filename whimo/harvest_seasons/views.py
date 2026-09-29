from typing import Any

from rest_framework import views
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.base import PaginatedDataResponse
from whimo.harvest_seasons.mappers import HarvestSeasonsMapper
from whimo.harvest_seasons.schemas.requests import HarvestSeasonListRequest
from whimo.harvest_seasons.services import HarvestSeasonsService


class HarvestSeasonsListView(views.APIView):
    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = HarvestSeasonListRequest.parse(request, from_query_params=True)
        items, pagination = HarvestSeasonsService.list_harvest_seasons(request=payload)

        response = HarvestSeasonsMapper.to_dto_list(items)
        return PaginatedDataResponse(data=response, pagination=pagination).as_response()
