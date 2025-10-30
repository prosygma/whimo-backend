from dataclasses import dataclass

from whimo.commodities.mappers.commodities import CommoditiesMapper
from whimo.commodities.schemas.dto import BalanceDTO
from whimo.db.models import Balance


@dataclass(slots=True)
class BalancesMapper:
    @staticmethod
    def to_dto(entity: Balance) -> BalanceDTO:
        commodity = CommoditiesMapper.to_dto_with_group(entity.commodity)

        return BalanceDTO(
            id=entity.id,
            volume=entity.volume,
            commodity=commodity,
        )

    @staticmethod
    def to_dto_list(entities: list[Balance]) -> list[BalanceDTO]:
        return [BalancesMapper.to_dto(entity) for entity in entities]
