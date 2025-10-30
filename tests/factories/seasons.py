from typing import Any, cast

import factory
import pytest

from tests.factories.base import BaseFactory
from tests.factories.commodities import CommodityFactory
from whimo.db.models import Commodity, Season, SeasonCommodity


class SeasonFactory(BaseFactory[Season]):
    class Meta:
        model = Season

    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=200)
    start_date = factory.Faker("date_between", start_date="-100d", end_date="-50d")
    end_date = factory.Faker("date_between", start_date="-40d", end_date="today")

    @factory.post_generation
    def with_commodities(self, is_created: bool, extracted: list[Commodity] | None, **__: Any) -> None:
        if not is_created or not extracted:
            return

        season = cast("Season", self)
        for commodity in extracted:
            SeasonCommodityFactory.create(season=season, commodity=commodity)


class SeasonCommodityFactory(BaseFactory[SeasonCommodity]):
    class Meta:
        model = SeasonCommodity

    season = factory.SubFactory(SeasonFactory)
    commodity = factory.SubFactory(CommodityFactory)


@pytest.fixture(autouse=True)
def reset_seasons_factories() -> None:
    SeasonFactory.reset_sequence()
    SeasonCommodityFactory.reset_sequence()
