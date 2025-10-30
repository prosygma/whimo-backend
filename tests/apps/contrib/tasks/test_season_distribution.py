from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory

from tests.factories.commodities import CommodityFactory
from tests.factories.seasons import SeasonCommodityFactory, SeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.contrib.tasks.season_distribution import distribute_transactions_over_seasons
from whimo.db.models import Transaction

pytestmark = [pytest.mark.django_db]


class TestSeasonDistributionTasks:
    def test_distribute_transactions_basic_assignment(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season == season

    def test_distribute_transactions_no_matching_seasons(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        other_commodity = CommodityFactory.create()

        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        SeasonCommodityFactory.create(season=season, commodity=other_commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season is None

    def test_distribute_transactions_date_range_mismatch(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() + timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=20),
        )
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season is None

    def test_distribute_transactions_multiple_seasons_priority(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()

        early_season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=20),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        late_season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )

        SeasonCommodityFactory.create(season=early_season, commodity=commodity)
        SeasonCommodityFactory.create(season=late_season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season == early_season

    def test_distribute_transactions_null_season_dates(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(start_date=None, end_date=None)
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season == season

    def test_distribute_transactions_null_start_date(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(start_date=None, end_date=DEFAULT_DATETIME.date() + timedelta(days=10))
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season == season

    def test_distribute_transactions_null_end_date(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(start_date=DEFAULT_DATETIME.date() - timedelta(days=10), end_date=None)
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season == season

    def test_distribute_transactions_missing_created_at(self) -> None:
        # Arrange
        commodity = CommodityFactory.create()
        season = SeasonFactory.create()
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transaction = TransactionFactory.create(commodity=commodity, season=None, created_at=None)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction.refresh_from_db()
        assert transaction.season is None

    def test_distribute_transactions_batch_processing(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transactions = TransactionFactory.create_batch(
            size=5, commodity=commodity, season=None, created_at=DEFAULT_DATETIME
        )

        # Act
        distribute_transactions_over_seasons(batch_size=3)

        # Assert
        for transaction in transactions:
            transaction.refresh_from_db()
            assert transaction.season == season

    def test_distribute_transactions_cursor_pagination(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transactions = TransactionFactory.create_batch(
            size=7, commodity=commodity, season=None, created_at=DEFAULT_DATETIME
        )

        # Act
        distribute_transactions_over_seasons(batch_size=2)

        # Assert
        for transaction in transactions:
            transaction.refresh_from_db()
            assert transaction.season == season

    def test_distribute_transactions_already_assigned_skip(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()

        season1 = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        season2 = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=5),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=15),
        )

        SeasonCommodityFactory.create(season=season1, commodity=commodity)
        SeasonCommodityFactory.create(season=season2, commodity=commodity)

        assigned_transaction = TransactionFactory.create(
            commodity=commodity, season=season2, created_at=DEFAULT_DATETIME
        )
        unassigned_transaction = TransactionFactory.create(
            commodity=commodity, season=None, created_at=DEFAULT_DATETIME
        )

        # Act
        distribute_transactions_over_seasons()

        # Assert
        assigned_transaction.refresh_from_db()
        unassigned_transaction.refresh_from_db()

        assert assigned_transaction.season == season2
        assert unassigned_transaction.season == season1

    def test_distribute_transactions_mixed_commodities(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity1 = CommodityFactory.create()
        commodity2 = CommodityFactory.create()

        season1 = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        season2 = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )

        SeasonCommodityFactory.create(season=season1, commodity=commodity1)
        SeasonCommodityFactory.create(season=season2, commodity=commodity2)

        transaction1 = TransactionFactory.create(commodity=commodity1, season=None, created_at=DEFAULT_DATETIME)
        transaction2 = TransactionFactory.create(commodity=commodity2, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction1.refresh_from_db()
        transaction2.refresh_from_db()

        assert transaction1.season == season1
        assert transaction2.season == season2

    def test_distribute_transactions_empty_result_set(self) -> None:
        # Arrange
        season = SeasonFactory.create()

        TransactionFactory.create(season=season)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transactions_without_season = Transaction.objects.filter(season__isnull=True)
        assert transactions_without_season.count() == 0

    def test_distribute_transactions_season_date_boundary_conditions(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()

        season_exact_start = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date(), end_date=DEFAULT_DATETIME.date() + timedelta(days=10)
        )
        season_exact_end = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10), end_date=DEFAULT_DATETIME.date()
        )

        SeasonCommodityFactory.create(season=season_exact_start, commodity=commodity)
        SeasonCommodityFactory.create(season=season_exact_end, commodity=commodity)

        transaction_start = TransactionFactory.create(commodity=commodity, season=None, created_at=DEFAULT_DATETIME)

        # Act
        distribute_transactions_over_seasons()

        # Assert
        transaction_start.refresh_from_db()
        assert transaction_start.season in [season_exact_start, season_exact_end]

    def test_distribute_transactions_large_batch_single_call(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        commodity = CommodityFactory.create()
        season = SeasonFactory.create(
            start_date=DEFAULT_DATETIME.date() - timedelta(days=10),
            end_date=DEFAULT_DATETIME.date() + timedelta(days=10),
        )
        SeasonCommodityFactory.create(season=season, commodity=commodity)

        transactions = TransactionFactory.create_batch(
            size=15, commodity=commodity, season=None, created_at=DEFAULT_DATETIME
        )

        # Act
        distribute_transactions_over_seasons(batch_size=1000)

        # Assert
        for transaction in transactions:
            transaction.refresh_from_db()
            assert transaction.season == season
