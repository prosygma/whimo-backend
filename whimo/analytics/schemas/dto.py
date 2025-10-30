from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from whimo.db.enums.transactions import TransactionTraceability


class ActiveTradersKPIDTO(BaseModel):
    count: int
    period_days: int = 30


class BalanceSummaryItemDTO(BaseModel):
    commodity_id: str
    commodity_code: str
    commodity_name: str
    commodity_unit: str
    total_volume: Decimal


class TraceabilityStatusDTO(BaseModel):
    status: TransactionTraceability
    count: int


class UserGrowthItemDTO(BaseModel):
    date: date
    registrations_count: int
    cumulative_count: int


class CurrentSeasonDTO(BaseModel):
    id: UUID
    name: str
    start_date: date | None
    end_date: date | None
    transactions_count: int


class SeasonTransactionsDailyDTO(BaseModel):
    date: date
    season_id: UUID
    season_name: str
    transactions_count: int


class SeasonTransactionsDTO(BaseModel):
    season_id: UUID
    season_name: str
    transactions_count: int


class UserMetricsDTO(BaseModel):
    total_transactions: int
    total_suppliers: int
    initial_plots: int
    files_uploaded: int


class AnalyticsDataDTO(BaseModel):
    active_traders: ActiveTradersKPIDTO
    balance_summary: list[BalanceSummaryItemDTO]
    transactions_by_traceability: list[TraceabilityStatusDTO]
    user_growth: list[UserGrowthItemDTO]
    current_seasons: list[CurrentSeasonDTO]
    season_transactions_daily: list[SeasonTransactionsDailyDTO]
    transactions_by_seasons: list[SeasonTransactionsDTO]
