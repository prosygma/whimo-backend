from decimal import Decimal

from whimo.common.schemas.dto import BaseModelDTO
from whimo.db.enums.transactions import TransactionTraceability
from whimo.harvest_seasons.schemas.dto import HarvestSeasonDTO


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
    harvest_season: HarvestSeasonDTO
    traceability: TransactionTraceability
    has_recipe: bool
