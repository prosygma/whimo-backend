import importlib
from datetime import date

import pytest
from django.apps import apps

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from whimo.db.models import HarvestSeason

split_group_fields_migration = importlib.import_module("whimo.db.migrations.0017_split_harvest_season_group_fields")

pytestmark = [pytest.mark.django_db]


class TestSplitHarvestSeasonGroupFieldsMigration:
    def test_backfills_group_year_month_and_duration(self) -> None:
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        season = HarvestSeasonFactory.create(
            commodity_group=group,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 9, 1),
        )
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)

        split_group_fields_migration.backfill_harvest_season_fields(apps, None)

        season.refresh_from_db()
        assert season.commodity_group_id == group.id
        assert season.year == 2025  # noqa: PLR2004 Magic value used in comparison
        assert season.start_month == 9  # noqa: PLR2004 Magic value used in comparison
        assert season.duration_months == 12  # noqa: PLR2004 Magic value used in comparison
        assert season.country == ""

    def test_backfills_a_six_month_season(self) -> None:
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        season = HarvestSeasonFactory.create(
            commodity_group=group,
            start_date=date(2026, 3, 1),
            end_date=date(2026, 9, 1),
        )
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)

        split_group_fields_migration.backfill_harvest_season_fields(apps, None)

        season.refresh_from_db()
        assert season.year == 2026  # noqa: PLR2004 Magic value used in comparison
        assert season.start_month == 3  # noqa: PLR2004 Magic value used in comparison
        assert season.duration_months == 6  # noqa: PLR2004 Magic value used in comparison

    def test_season_spanning_more_than_one_group_stops_the_run(self) -> None:
        season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        cocoa = CommodityFactory.create(with_harvest_season=False)
        butter = CommodityFactory.create(with_harvest_season=False)
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=cocoa)
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=butter)

        with pytest.raises(RuntimeError, match=str(season.pk)):
            split_group_fields_migration.backfill_harvest_season_fields(apps, None)

    def test_season_with_no_commodities_stops_the_run(self) -> None:
        season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))

        with pytest.raises(RuntimeError, match=str(season.pk)):
            split_group_fields_migration.backfill_harvest_season_fields(apps, None)

    def test_span_that_is_neither_six_nor_twelve_months_stops_the_run(self) -> None:
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group, with_harvest_season=False)
        season = HarvestSeasonFactory.create(
            commodity_group=group,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 3, 1),
        )
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)
        # Force an off-grid span directly in the database, bypassing model-level validation.
        HarvestSeason.objects.filter(pk=season.pk).update(end_date=date(2026, 4, 1))

        with pytest.raises(RuntimeError, match=str(season.pk)):
            split_group_fields_migration.backfill_harvest_season_fields(apps, None)
