from uuid import UUID

from whimo.common.schemas.base import PaginationRequest


class CommodityListRequest(PaginationRequest):
    search: str | None = None
    group_id: UUID | None = None


class CommodityGroupListRequest(PaginationRequest):
    search: str | None = None


class BalanceListRequest(PaginationRequest):
    search: str | None = None
    commodity_group_id: UUID | None = None
    commodity_id: UUID | None = None
