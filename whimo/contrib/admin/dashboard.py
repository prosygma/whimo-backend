from django.core.handlers.wsgi import WSGIRequest

from whimo.analytics.services import AnalyticsService


def dashboard_callback(_: WSGIRequest, context: dict) -> dict:
    analytics_data = AnalyticsService.get_analytics_data()

    context.update(
        {
            "title": "Dashboard",
            "analytics_data": analytics_data,
            "active_traders": analytics_data.active_traders,
            "balance_summary": analytics_data.balance_summary,
            "traceability_stats": analytics_data.transactions_by_traceability,
            "user_growth": analytics_data.user_growth,
            "current_seasons": analytics_data.current_seasons,
            "season_transactions_daily": analytics_data.season_transactions_daily,
            "transactions_by_seasons": analytics_data.transactions_by_seasons,
        }
    )

    return context
