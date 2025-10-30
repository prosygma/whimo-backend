from dataclasses import dataclass

from django.utils.translation import gettext as _

from whimo.commodities.mappers.commodities_groups import CommoditiesGroupsMapper
from whimo.commodities.schemas.dto import CommodityDTO, CommodityWithBalanceDTO, CommodityWithGroupDTO
from whimo.db.models import Commodity


@dataclass(slots=True)
class CommoditiesMapper:
    @staticmethod
    def to_dto(commodity: Commodity) -> CommodityDTO:
        return CommodityDTO(
            id=commodity.id,
            code=commodity.code,
            name=_(commodity.name),
            unit=commodity.unit,
        )

    @staticmethod
    def to_dto_with_group(commodity: Commodity) -> CommodityWithGroupDTO:
        group = CommoditiesGroupsMapper.to_dto(commodity.group)

        return CommodityWithGroupDTO(
            id=commodity.id,
            code=commodity.code,
            name=_(commodity.name),
            unit=commodity.unit,
            group=group,
        )

    @staticmethod
    def to_dto_list(commodities: list[Commodity]) -> list[CommodityDTO]:
        return [CommoditiesMapper.to_dto(commodity) for commodity in commodities]

    @staticmethod
    def to_dto_list_with_group(commodities: list[Commodity]) -> list[CommodityWithGroupDTO]:
        return [CommoditiesMapper.to_dto_with_group(commodity) for commodity in commodities]

    @staticmethod
    def to_dto_with_balance(commodity: Commodity) -> CommodityWithBalanceDTO:
        group = CommoditiesGroupsMapper.to_dto(commodity.group)

        return CommodityWithBalanceDTO(
            id=commodity.id,
            code=commodity.code,
            name=_(commodity.name),
            unit=commodity.unit,
            group=group,
            balance=commodity.balance,
        )

    @staticmethod
    def to_dto_list_with_balance(commodities: list[Commodity]) -> list[CommodityWithBalanceDTO]:
        return [CommoditiesMapper.to_dto_with_balance(commodity) for commodity in commodities]
