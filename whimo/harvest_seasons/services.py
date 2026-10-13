import logging
from dataclasses import dataclass
from typing import cast

from django.db.models import QuerySet

from whimo.common.schemas.base import Pagination
from whimo.common.utils import paginate_queryset
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import Commodity, HarvestSeason, HarvestSeasonCommodity
from whimo.harvest_seasons.schemas.requests import HarvestSeasonListRequest

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HarvestSeasonsService:
    @staticmethod
    def list_harvest_seasons(request: HarvestSeasonListRequest) -> tuple[list[HarvestSeason], Pagination]:
        queryset = HarvestSeasonsService._filter_harvest_seasons(request)
        return paginate_queryset(queryset=queryset, request=request)

    @staticmethod
    def create_next_season(previous_season: HarvestSeason) -> HarvestSeason | None:
        commodity = Commodity.objects.filter(group_id=previous_season.commodity_group_id).first()
        if commodity is None:
            logger.warning(
                "Commodity group %s has no commodities left; skipping season rollover",
                previous_season.commodity_group_id,
            )
            return None

        next_season = HarvestSeason(
            country=previous_season.country,
            commodity_group_id=previous_season.commodity_group_id,
            year=previous_season.year + 1,
            start_month=previous_season.start_month,
            duration_months=previous_season.duration_months,
            status=HarvestSeasonStatus.ACTIVE,
        )
        next_season.save()

        HarvestSeasonCommodity.objects.create(
            harvest_season=next_season,
            commodity=commodity,
            period=next_season.period,
            status=next_season.status,
        )
        return next_season

    @staticmethod
    def _filter_harvest_seasons(params: HarvestSeasonListRequest) -> QuerySet[HarvestSeason]:
        queryset = HarvestSeason.objects.all()

        for commodity_id in dict.fromkeys(params.commodity_id or []):
            queryset = queryset.filter(harvest_season_commodities__commodity_id=commodity_id)

        if commodity_group_id := params.commodity_group_id:
            queryset = queryset.filter(
                harvest_season_commodities__commodity__group_id=commodity_group_id,
            ).distinct()

        if status := params.status:
            queryset = queryset.filter(status=status)

        return cast(QuerySet[HarvestSeason], queryset)
