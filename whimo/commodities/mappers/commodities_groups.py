from dataclasses import dataclass

from django.utils.translation import gettext as _

from whimo.commodities.schemas.dto import (
    CommodityGroupDTO,
    CommodityGroupWithCommoditiesBalancesDTO,
)
from whimo.db.models import CommodityGroup


@dataclass(slots=True)
class CommoditiesGroupsMapper:
    @staticmethod
    def to_dto(commodity_group: CommodityGroup) -> CommodityGroupDTO:
        return CommodityGroupDTO(
            id=commodity_group.id,
            name=_(commodity_group.name),
        )

    @staticmethod
    def to_dto_with_commodities_balances(commodity_group: CommodityGroup) -> CommodityGroupWithCommoditiesBalancesDTO:
        from whimo.commodities.mappers.commodities import CommoditiesMapper

        commodities = CommoditiesMapper.to_dto_list_with_balance(list(commodity_group.commodities.all()))

        return CommodityGroupWithCommoditiesBalancesDTO(
            id=commodity_group.id,
            name=_(commodity_group.name),
            commodities=commodities,
        )

    @staticmethod
    def to_dto_list_with_commodities_balances(
        entities: list[CommodityGroup],
    ) -> list[CommodityGroupWithCommoditiesBalancesDTO]:
        return [CommoditiesGroupsMapper.to_dto_with_commodities_balances(entity) for entity in entities]
