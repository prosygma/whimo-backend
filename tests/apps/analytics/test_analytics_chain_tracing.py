from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from whimo.analytics.services import AnalyticsService
from whimo.db.enums.transactions import TransactionStatus

pytestmark = [pytest.mark.django_db]


class TestAnalyticsChainTracing:
    def teardown_method(self) -> None:
        cache.clear()

    @patch("whimo.analytics.services.default_storage.exists")
    def test_single_transaction(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1
        assert result.initial_plots == 1

    @patch("whimo.analytics.services.default_storage.exists")
    def test_linear_chain(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        farmer = UserFactory.create()
        trader = UserFactory.create()
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=farmer,
            buyer=trader,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=trader,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1
        assert result.total_suppliers == 1
        assert result.initial_plots == 2  # noqa: PLR2004

    def test_branching_chain(self) -> None:
        # Arrange
        farmer1 = UserFactory.create()
        farmer2 = UserFactory.create()
        trader = UserFactory.create()
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=farmer1,
            buyer=trader,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=farmer2,
            buyer=trader,
            commodity=commodity,
            farm_latitude=Decimal("12.345"),
            farm_longitude=Decimal("23.678"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=trader,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1
        assert result.total_suppliers == 1
        assert result.initial_plots == 3  # noqa: PLR2004

    @patch("whimo.analytics.services.default_storage.exists")
    def test_duplicate_coordinates(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        farmer = UserFactory.create()
        trader = UserFactory.create()
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        same_latitude = Decimal("10.123")
        same_longitude = Decimal("20.456")

        TransactionFactory.create(
            seller=farmer,
            buyer=trader,
            commodity=commodity,
            farm_latitude=same_latitude,
            farm_longitude=same_longitude,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=trader,
            buyer=user,
            commodity=commodity,
            farm_latitude=same_latitude,  # Same coordinates
            farm_longitude=same_longitude,  # Same coordinates
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1
        assert result.initial_plots == 1  # Should deduplicate to 1 unique farm plot

    @patch("whimo.analytics.services.default_storage.exists")
    def test_multiple_commodities(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        user = UserFactory.create()
        supplier1 = UserFactory.create()
        supplier2 = UserFactory.create()
        commodity1 = CommodityFactory.create()
        commodity2 = CommodityFactory.create()

        TransactionFactory.create(
            seller=supplier1,
            buyer=user,
            commodity=commodity1,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=supplier2,
            buyer=user,
            commodity=commodity2,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 2  # noqa: PLR2004
        assert result.total_suppliers == 2  # noqa: PLR2004
        assert result.initial_plots == 2  # noqa: PLR2004

    @patch("whimo.analytics.services.default_storage.exists")
    def test_rejected_transactions(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        farmer = UserFactory.create()
        trader = UserFactory.create()
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=farmer,
            buyer=trader,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.REJECTED,
        )

        TransactionFactory.create(
            seller=trader,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1
        assert result.initial_plots == 1  # Should only count the accepted transaction's farm plot

    def test_pending_transactions(self) -> None:
        # Arrange
        user = UserFactory.create()
        supplier = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=supplier,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.PENDING,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 1  # Pending transactions count for user
        assert result.total_suppliers == 1
        assert result.initial_plots == 1

    def test_missing_coordinates(self) -> None:
        # Arrange
        user = UserFactory.create()
        supplier = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=supplier,
            buyer=user,
            commodity=commodity,
            farm_latitude=None,
            farm_longitude=None,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=supplier,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=None,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=supplier,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 3  # noqa: PLR2004
        assert result.initial_plots == 1

    @patch("whimo.analytics.services.default_storage.exists")
    def test_multiple_roles(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        user = UserFactory.create()
        trader1 = UserFactory.create()
        trader2 = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=trader1,
            buyer=user,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=user,
            buyer=trader2,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            created_by=user,
            commodity=commodity,
            farm_latitude=Decimal("12.345"),
            farm_longitude=Decimal("23.678"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user.id)

        # Assert
        assert result.total_transactions == 3  # noqa: PLR2004
        assert result.total_suppliers == 1
        assert result.initial_plots == 3  # noqa: PLR2004

    @patch("whimo.analytics.services.default_storage.exists")
    def test_circular_references(self, mock_storage_exists: Mock) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            seller=user1,
            buyer=user2,
            commodity=commodity,
            farm_latitude=Decimal("10.123"),
            farm_longitude=Decimal("20.456"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            seller=user2,
            buyer=user1,
            commodity=commodity,
            farm_latitude=Decimal("11.789"),
            farm_longitude=Decimal("21.987"),
            status=TransactionStatus.ACCEPTED,
        )

        # Act
        result = AnalyticsService.get_user_analytics_data(user1.id)

        # Assert
        assert result.total_transactions == 2  # noqa: PLR2004
        assert result.total_suppliers == 1
        assert result.initial_plots == 2  # noqa: PLR2004
