from datetime import date
from typing import Any, cast

import factory
import pytest

from tests.factories.base import BaseFactory
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import Commodity, HarvestSeason, HarvestSeasonCommodity


class HarvestSeasonFactory(BaseFactory[HarvestSeason]):
    class Meta:
        model = HarvestSeason

    commodity_group = factory.SubFactory("tests.factories.commodities.CommodityGroupFactory")
    year = None
    # Only fall back to a default date range when the caller didn't ask for year/start_month/duration
    # instead - passing both would fail the model's own "which one did you mean" check.
    start_date = factory.Maybe("year", yes_declaration=None, no_declaration=date(2025, 9, 1))
    end_date = factory.Maybe("year", yes_declaration=None, no_declaration=date(2026, 9, 1))
    status = HarvestSeasonStatus.ACTIVE

    @factory.post_generation
    def with_commodities(self, is_created: bool, extracted: list[Commodity] | None, **__: Any) -> None:
        if not is_created or not extracted:
            return

        harvest_season = cast("HarvestSeason", self)
        for commodity in extracted:
            if harvest_season.commodities.filter(pk=commodity.pk).exists():
                continue
            HarvestSeasonCommodityFactory.create(harvest_season=harvest_season, commodity=commodity)


class HarvestSeasonCommodityFactory(BaseFactory[HarvestSeasonCommodity]):
    class Meta:
        model = HarvestSeasonCommodity

    harvest_season = factory.SubFactory(HarvestSeasonFactory)
    commodity = factory.SubFactory(
        "tests.factories.commodities.CommodityFactory",
        group=factory.SelfAttribute("..harvest_season.commodity_group"),
    )


@pytest.fixture(autouse=True)
def reset_harvest_seasons_factories() -> None:
    HarvestSeasonFactory.reset_sequence()
    HarvestSeasonCommodityFactory.reset_sequence()
