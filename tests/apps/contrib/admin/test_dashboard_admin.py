from unittest.mock import MagicMock, patch

import pytest
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory

from whimo.contrib.admin.dashboard import dashboard_callback

pytestmark = [pytest.mark.django_db]


class TestDashboardAdmin:
    def test_dashboard_callback(self) -> None:
        # Arrange
        factory = RequestFactory()
        request = factory.get("/admin/")
        wsgi_request = WSGIRequest(request.environ)

        mock_analytics_data = MagicMock()
        mock_analytics_data.active_traders = "mock_active_traders"
        mock_analytics_data.balance_summary = "mock_balance_summary"
        mock_analytics_data.transactions_by_traceability = "mock_traceability_stats"
        mock_analytics_data.user_growth = "mock_user_growth"

        context = {"existing_key": "existing_value"}

        # Act
        with patch(
            "whimo.contrib.admin.dashboard.AnalyticsService.get_analytics_data", return_value=mock_analytics_data
        ):
            result = dashboard_callback(wsgi_request, context)

        # Assert
        assert "existing_key" in result
        assert result["existing_key"] == "existing_value"
        assert result["title"] == "Dashboard"
        assert result["analytics_data"] == mock_analytics_data
        assert result["active_traders"] == "mock_active_traders"
        assert result["balance_summary"] == "mock_balance_summary"
        assert result["traceability_stats"] == "mock_traceability_stats"
        assert result["user_growth"] == "mock_user_growth"
