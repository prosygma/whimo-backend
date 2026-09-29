from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.helpers.constants import DEFAULT_DATETIME, SMALL_BATCH_SIZE
from whimo.contrib.tasks.harvest_seasons import transition_harvest_seasons
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import HarvestSeason
from whimo.harvest_seasons.services import HarvestSeasonsService

pytestmark = [pytest.mark.django_db]


class TestTransitionHarvestSeasons:
    def test_elapsed_active_season_transitions_and_archives_previous_past(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        past = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2018,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.PAST,
        )
        active = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=past, commodity=commodity)
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=commodity)

        # Act
        transition_harvest_seasons()

        # Assert
        past.refresh_from_db()
        active.refresh_from_db()
        assert past.status == HarvestSeasonStatus.ARCHIVED
        assert active.status == HarvestSeasonStatus.PAST

        next_season = HarvestSeason.objects.get(commodity_group=group, year=2020)
        assert next_season.status == HarvestSeasonStatus.ACTIVE
        assert next_season.start_month == 1
        assert next_season.duration_months == 12  # noqa: PLR2004 Magic value used in comparison
        assert next_season.country == active.country
        assert set(next_season.commodities.all()) == {commodity}

    def test_elapsed_active_season_with_no_previous_past_only_creates_the_next_one(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        active = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=commodity)

        # Act
        transition_harvest_seasons()

        # Assert
        active.refresh_from_db()
        assert active.status == HarvestSeasonStatus.PAST
        assert HarvestSeason.objects.filter(
            commodity_group=group, year=2020, status=HarvestSeasonStatus.ACTIVE
        ).exists()

    def test_season_not_yet_elapsed_is_left_untouched(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        active = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2020,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=commodity)

        # Act
        transition_harvest_seasons()

        # Assert
        active.refresh_from_db()
        assert active.status == HarvestSeasonStatus.ACTIVE
        assert not HarvestSeason.objects.filter(commodity_group=group, year=2021).exists()

    def test_no_commodities_left_transitions_but_skips_the_next_season(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange: every commodity was reassigned or deleted after the season was created, so the
        # rollover has nothing left to link the next season to.
        freezer.move_to(DEFAULT_DATETIME)
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        active = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=commodity)
        commodity.delete()

        # Act
        transition_harvest_seasons()

        # Assert
        active.refresh_from_db()
        assert active.status == HarvestSeasonStatus.PAST
        assert not HarvestSeason.objects.filter(commodity_group=group, year=2020).exists()

    def test_a_failing_group_does_not_block_another_groups_transition(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        broken_group = CommodityGroupFactory.create()
        broken_commodity = CommodityFactory.create(group=broken_group, with_harvest_season=False)
        broken_season = HarvestSeasonFactory.create(
            commodity_group=broken_group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=broken_season, commodity=broken_commodity)

        healthy_group = CommodityGroupFactory.create()
        healthy_commodity = CommodityFactory.create(group=healthy_group, with_harvest_season=False)
        healthy_season = HarvestSeasonFactory.create(
            commodity_group=healthy_group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=healthy_season, commodity=healthy_commodity)

        original = HarvestSeasonsService.create_next_season

        def fail_only_for_broken_group(previous_season: HarvestSeason) -> HarvestSeason | None:
            if previous_season.commodity_group_id == broken_group.id:
                raise RuntimeError("boom")
            return original(previous_season)

        # Act
        with patch(
            "whimo.harvest_seasons.services.HarvestSeasonsService.create_next_season",
            side_effect=fail_only_for_broken_group,
        ):
            transition_harvest_seasons()

        # Assert: the broken group's own transaction rolled back entirely, the healthy one didn't.
        broken_season.refresh_from_db()
        healthy_season.refresh_from_db()
        assert broken_season.status == HarvestSeasonStatus.ACTIVE
        assert not HarvestSeason.objects.filter(commodity_group=broken_group, year=2020).exists()
        assert healthy_season.status == HarvestSeasonStatus.PAST
        assert HarvestSeason.objects.filter(commodity_group=healthy_group, year=2020).exists()

    def test_running_twice_does_not_double_transition(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        active = HarvestSeasonFactory.create(
            commodity_group=group,
            year=2019,
            start_month=1,
            duration_months=12,
            status=HarvestSeasonStatus.ACTIVE,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=commodity)

        # Act
        transition_harvest_seasons()
        transition_harvest_seasons()

        # Assert
        assert HarvestSeason.objects.filter(commodity_group=group).count() == SMALL_BATCH_SIZE
        next_season = HarvestSeason.objects.get(commodity_group=group, year=2020)
        assert next_season.status == HarvestSeasonStatus.ACTIVE
