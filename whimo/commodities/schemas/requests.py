from uuid import UUID

from whimo.common.schemas.base import OrderingRequestMixin, PaginationRequest


class CommodityListRequest(PaginationRequest):
    search: str | None = None
    group_id: UUID | None = None


class CommodityGroupListRequest(PaginationRequest):
    search: str | None = None


class BalanceListRequest(PaginationRequest, OrderingRequestMixin):
    search: str | None = None
    commodity_group_id: UUID | None = None
    commodity_id: UUID | None = None

    @property
    def orderings_map(self) -> dict[str, str]:
        return {
            "commodity_name": "commodity__name",
            "amount": "volume",
        }
