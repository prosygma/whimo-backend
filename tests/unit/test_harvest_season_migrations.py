import importlib
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from django.apps import apps
from freezegun.api import FrozenDateTimeFactory

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from whimo.db.enums import HarvestSeasonStatus, TransactionStatus, TransactionType
from whimo.db.models import Commodity, HarvestSeason, HarvestSeasonCommodity

stamp_chains_migration = importlib.import_module("whimo.db.migrations.0010_stamp_chains_with_harvest_season")
cover_whole_groups_migration = importlib.import_module("whimo.db.migrations.0012_cover_whole_commodity_groups")

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def commodity() -> Commodity:
    return CommodityFactory.create(with_harvest_season=False)


@pytest.fixture
def past_season(commodity: Commodity) -> HarvestSeason:
    season = HarvestSeasonFactory.create(
        start_date=date(2024, 9, 1),
        end_date=date(2025, 9, 1),
        status=HarvestSeasonStatus.PAST,
    )
    HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)
    return season


@pytest.fixture
def active_season(commodity: Commodity) -> HarvestSeason:
    season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
    HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)
    return season


class TestStampChainsMigration:
    def test_a_coverage_gap_stops_the_run_and_names_the_commodity_and_date(
        self,
        freezer: FrozenDateTimeFactory,
        commodity: Commodity,
        active_season: HarvestSeason,
    ) -> None:
        freezer.move_to(datetime(2020, 1, 1, tzinfo=UTC))
        TransactionFactory.create(producer=True, commodity=commodity, harvest_season=active_season)

        with pytest.raises(RuntimeError, match=f"{commodity.id} on 2020-01-01"):
            stamp_chains_migration.stamp_chains(apps, None)

    def test_a_chain_takes_the_season_of_its_first_transaction(
        self,
        freezer: FrozenDateTimeFactory,
        commodity: Commodity,
        past_season: HarvestSeason,
        active_season: HarvestSeason,
    ) -> None:
        trader = UserFactory.create()
        freezer.move_to(datetime(2025, 8, 1, tzinfo=UTC))
        TransactionFactory.create(producer=True, buyer=trader, commodity=commodity, harvest_season=past_season)
        freezer.move_to(datetime(2025, 10, 1, tzinfo=UTC))
        sale = TransactionFactory.create(
            seller=trader,
            created_by=trader,
            commodity=commodity,
            harvest_season=active_season,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
        )

        stamp_chains_migration.stamp_chains(apps, None)

        sale.refresh_from_db()
        assert sale.harvest_season_id == past_season.id


class TestCoverWholeGroupsMigration:
    def test_a_conversion_split_across_seasons_stops_the_run(
        self,
        commodity: Commodity,
        past_season: HarvestSeason,
        active_season: HarvestSeason,
    ) -> None:
        group_id = uuid4()
        for season in (past_season, active_season):
            TransactionFactory.create(
                type=TransactionType.CONVERSION,
                group_id=group_id,
                commodity=commodity,
                harvest_season=season,
            )

        with pytest.raises(RuntimeError, match=str(group_id)):
            cover_whole_groups_migration.cover_whole_groups(apps, None)

    @pytest.mark.parametrize(
        ("first_status", "second_start_date", "second_end_date"),
        [
            (HarvestSeasonStatus.ACTIVE, date(2026, 9, 1), date(2027, 9, 1)),
            (HarvestSeasonStatus.PAST, date(2026, 3, 1), date(2026, 9, 1)),
        ],
    )
    def test_conflicting_seasons_in_one_group_stop_the_run(
        self,
        first_status: HarvestSeasonStatus,
        second_start_date: date,
        second_end_date: date,
    ) -> None:
        group = CommodityGroupFactory.create()
        cocoa, butter = CommodityFactory.create_batch(size=2, group=group, with_harvest_season=False)
        first = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1), status=first_status)
        second = HarvestSeasonFactory.create(start_date=second_start_date, end_date=second_end_date)
        HarvestSeasonCommodity.objects.bulk_create(
            HarvestSeasonCommodity(
                harvest_season=season,
                commodity=commodity,
                period=season.period,
                status=season.status,
            )
            for season, commodity in ((first, cocoa), (second, butter))
        )

        with pytest.raises(RuntimeError, match=str(group.id)):
            cover_whole_groups_migration.cover_whole_groups(apps, None)
