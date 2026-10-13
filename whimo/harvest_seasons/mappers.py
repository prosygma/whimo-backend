from dataclasses import dataclass

from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import HarvestSeason
from whimo.harvest_seasons.schemas.dto import HarvestSeasonDTO


@dataclass(slots=True)
class HarvestSeasonsMapper:
    @staticmethod
    def to_dto(harvest_season: HarvestSeason) -> HarvestSeasonDTO:
        return HarvestSeasonDTO(
            id=harvest_season.id,
            name=harvest_season.name,
            start_date=harvest_season.start_date,
            end_date=harvest_season.end_date,
            status=HarvestSeasonStatus(harvest_season.status),
        )

    @staticmethod
    def to_dto_list(harvest_seasons: list[HarvestSeason]) -> list[HarvestSeasonDTO]:
        return [HarvestSeasonsMapper.to_dto(harvest_season) for harvest_season in harvest_seasons]
