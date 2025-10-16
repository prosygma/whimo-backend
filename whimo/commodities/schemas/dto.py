from decimal import Decimal

from whimo.common.schemas.dto import BaseModelDTO


class CommodityGroupDTO(BaseModelDTO):
    name: str


class CommodityDTO(BaseModelDTO):
    code: str
    name: str
    unit: str
    has_recipe: bool


class CommodityWithGroupDTO(CommodityDTO):
    group: CommodityGroupDTO


class CommodityWithBalanceDTO(CommodityWithGroupDTO):
    balance: Decimal | None


class CommodityGroupWithCommoditiesBalancesDTO(BaseModelDTO):
    name: str
    commodities: list[CommodityWithBalanceDTO]


class BalanceDTO(BaseModelDTO):
    volume: Decimal
    commodity: CommodityWithGroupDTO
    has_recipe: bool
