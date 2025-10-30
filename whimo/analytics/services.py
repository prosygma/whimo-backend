from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast
from uuid import UUID

from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models import Count, Q, QuerySet, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.translation import gettext as _

from whimo.analytics.constants import USER_ANALYTICS_CACHE_KEY, USER_ANALYTICS_CACHE_TIMEOUT
from whimo.analytics.schemas.dto import (
    ActiveTradersKPIDTO,
    AnalyticsDataDTO,
    BalanceSummaryItemDTO,
    CurrentSeasonDTO,
    SeasonTransactionsDailyDTO,
    SeasonTransactionsDTO,
    TraceabilityStatusDTO,
    UserGrowthItemDTO,
    UserMetricsDTO,
)
from whimo.common.utils import get_user_model
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Balance, Season, Transaction
from whimo.transactions.constants import LOCATION_S3_PREFIX

User = get_user_model()


@dataclass(slots=True)
class AnalyticsService:
    @staticmethod
    def get_analytics_data() -> AnalyticsDataDTO:
        active_traders = AnalyticsService._get_active_traders_kpi()
        balance_summary = AnalyticsService._get_balance_summary()
        traceability_stats = AnalyticsService._get_transactions_by_traceability()
        user_growth = AnalyticsService._get_user_growth_data()

        current_seasons_queryset = Season.objects.current_seasons()
        current_seasons = AnalyticsService._get_current_seasons(current_seasons_queryset)
        season_transactions_daily = AnalyticsService._get_season_transactions_daily(current_seasons_queryset)
        transactions_by_seasons = AnalyticsService._get_transactions_by_seasons(current_seasons_queryset)

        return AnalyticsDataDTO(
            active_traders=active_traders,
            balance_summary=balance_summary,
            transactions_by_traceability=traceability_stats,
            user_growth=user_growth,
            current_seasons=current_seasons,
            season_transactions_daily=season_transactions_daily,
            transactions_by_seasons=transactions_by_seasons,
        )

    @staticmethod
    def _get_active_traders_kpi(period_days: int = 30) -> ActiveTradersKPIDTO:
        cutoff_date = timezone.now() - timedelta(days=period_days)

        recent_transactions = Transaction.objects.filter(created_at__gte=cutoff_date)

        buyer_ids = set(recent_transactions.filter(buyer_id__isnull=False).values_list("buyer_id", flat=True))
        seller_ids = set(recent_transactions.filter(seller_id__isnull=False).values_list("seller_id", flat=True))

        active_trader_ids = buyer_ids.union(seller_ids)

        return ActiveTradersKPIDTO(
            count=len(active_trader_ids),
            period_days=period_days,
        )

    @staticmethod
    def _get_balance_summary() -> list[BalanceSummaryItemDTO]:
        balance_summary = (
            Balance.objects.select_related("commodity")
            .values("commodity_id", "commodity__code", "commodity__name", "commodity__unit")
            .annotate(total_volume=Sum("volume"))
            .filter(total_volume__gt=0)
            .order_by("commodity__code")
        )

        return [
            BalanceSummaryItemDTO(
                commodity_id=str(item["commodity_id"]),
                commodity_code=item["commodity__code"],
                commodity_name=_(item["commodity__name"]),
                commodity_unit=item["commodity__unit"],
                total_volume=item["total_volume"],
            )
            for item in balance_summary
        ]

    @staticmethod
    def _get_transactions_by_traceability() -> list[TraceabilityStatusDTO]:
        traceability_counts = (
            Transaction.objects.filter(traceability__isnull=False)
            .values("traceability")
            .annotate(count=Count("id"))
            .order_by("traceability")
        )

        return [
            TraceabilityStatusDTO(
                status=TransactionTraceability(item["traceability"]),
                count=item["count"],
            )
            for item in traceability_counts
            if item["traceability"]
        ]

    @staticmethod
    def _get_user_growth_data() -> list[UserGrowthItemDTO]:
        daily_registrations = (
            User.objects.filter(is_deleted=False)
            .annotate(registration_date=TruncDate("date_joined"))
            .values("registration_date")
            .annotate(registrations_count=Count("id"))
            .order_by("registration_date")
        )

        cumulative_count = 0
        result = []
        for item in daily_registrations:
            cumulative_count += item["registrations_count"]
            result.append(
                UserGrowthItemDTO(
                    date=item["registration_date"],
                    registrations_count=item["registrations_count"],
                    cumulative_count=cumulative_count,
                )
            )

        return result

    @staticmethod
    def _get_current_seasons(current_seasons_queryset: QuerySet[Season]) -> list[CurrentSeasonDTO]:
        return [
            CurrentSeasonDTO(
                id=season.id,
                name=_(season.name),
                start_date=season.start_date,
                end_date=season.end_date,
                transactions_count=season.transactions_count,
            )
            for season in current_seasons_queryset
        ]

    @staticmethod
    def _get_season_transactions_daily(current_seasons_queryset: QuerySet[Season]) -> list[SeasonTransactionsDailyDTO]:
        daily_transactions = (
            Transaction.objects.filter(season__in=current_seasons_queryset)
            .select_related("season")
            .annotate(transaction_date=TruncDate("created_at"))
            .values("transaction_date", "season_id", "season__name")
            .annotate(transactions_count=Count("id"))
            .order_by("season__start_date", "transaction_date")
        )

        return [
            SeasonTransactionsDailyDTO(
                date=item["transaction_date"],
                season_id=item["season_id"],
                season_name=_(item["season__name"]),
                transactions_count=item["transactions_count"],
            )
            for item in daily_transactions
        ]

    @staticmethod
    def _get_transactions_by_seasons(current_seasons_queryset: QuerySet[Season]) -> list[SeasonTransactionsDTO]:
        return [
            SeasonTransactionsDTO(
                season_id=season.id,
                season_name=_(season.name),
                transactions_count=season.transactions_count,
            )
            for season in current_seasons_queryset
        ]

    @staticmethod
    def get_user_analytics_data(user_id: UUID) -> UserMetricsDTO:
        cache_key = USER_ANALYTICS_CACHE_KEY.format(user_id=user_id)
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return UserMetricsDTO.model_validate(cached_data)

        total_transactions = AnalyticsService._get_user_transactions_count(user_id)
        total_suppliers = AnalyticsService._get_user_suppliers_count(user_id)
        initial_plots = AnalyticsService._get_user_plots_count(user_id)
        files_uploaded = AnalyticsService._get_user_files_count(user_id)

        analytics_data = UserMetricsDTO(
            total_transactions=total_transactions,
            total_suppliers=total_suppliers,
            initial_plots=initial_plots,
            files_uploaded=files_uploaded,
        )

        cache.set(cache_key, analytics_data.model_dump(), timeout=USER_ANALYTICS_CACHE_TIMEOUT)

        return analytics_data

    @staticmethod
    def _get_user_transactions_count(user_id: UUID) -> int:
        return Transaction.objects.filter(Q(buyer_id=user_id) | Q(seller_id=user_id) | Q(created_by_id=user_id)).count()

    @staticmethod
    def _get_user_suppliers_count(user_id: UUID) -> int:
        return (
            Transaction.objects.filter(buyer_id=user_id, seller_id__isnull=False).values("seller_id").distinct().count()
        )

    @staticmethod
    def _get_user_plots_count(user_id: UUID) -> int:
        user_transactions = Transaction.objects.filter(
            Q(buyer_id=user_id) | Q(seller_id=user_id) | Q(created_by_id=user_id)
        )

        unique_plots = set()

        for transaction in user_transactions:
            chain_transactions = AnalyticsService._get_all_chain_transactions_for_user(
                transaction.id, transaction.commodity_id
            )

            for chain_tx in chain_transactions:
                if chain_tx.farm_latitude is not None and chain_tx.farm_longitude is not None:
                    plot_key = (chain_tx.farm_latitude, chain_tx.farm_longitude)
                    unique_plots.add(plot_key)

        return len(unique_plots)

    @staticmethod
    def _get_all_chain_transactions_for_user(transaction_id: UUID, commodity_id: UUID) -> QuerySet[Transaction]:
        from whimo.db.enums.transactions import TransactionStatus

        chain_transactions = Transaction.objects.none()
        base_query = Transaction.objects.filter(commodity_id=commodity_id)

        transactions_ids = {transaction_id}
        filters: dict[str, Any] = {}
        visited: set[UUID] = set()

        while transactions_ids:
            filters["pk__in"] = transactions_ids
            transactions_query = base_query.filter(**filters).exclude(pk__in=visited)
            chain_transactions |= transactions_query

            filters["status"] = TransactionStatus.ACCEPTED
            visited |= transactions_ids

            sellers_ids = transactions_query.filter(seller_id__isnull=False).values_list("seller_id", flat=True)
            transactions_ids = set(base_query.filter(buyer_id__in=sellers_ids).values_list("pk", flat=True))

        return cast(QuerySet[Transaction], chain_transactions)

    @staticmethod
    def _get_user_files_count(user_id: UUID) -> int:
        transactions = Transaction.objects.filter(created_by_id=user_id).values_list("id", flat=True)

        files_count = 0
        for transaction_id in transactions:
            file_path = f"{LOCATION_S3_PREFIX}/{transaction_id}"
            if default_storage.exists(file_path):
                files_count += 1

        return files_count
