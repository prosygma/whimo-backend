from typing import Any, cast

import factory
import pytest

from tests.factories.base import BaseFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory
from whimo.db.models import Commodity, CommodityGroup, HarvestSeason


class CommodityGroupFactory(BaseFactory[CommodityGroup]):
    class Meta:
        model = CommodityGroup

    name = factory.Faker("word")


class CommodityFactory(BaseFactory[Commodity]):
    class Meta:
        model = Commodity

    code = factory.Faker("numerify", text="####")
    name = factory.Faker("word")
    unit = factory.Faker("random_element", elements=["kg", "pcs", "tons", "liters"])
    group = factory.SubFactory(CommodityGroupFactory)

    @factory.post_generation
    def with_harvest_season(self, is_created: bool, extracted: "HarvestSeason | bool | None", **__: Any) -> None:
        if not is_created or extracted is False:
            return

        commodity = cast("Commodity", self)
        if isinstance(extracted, HarvestSeason):
            if commodity.harvest_seasons.filter(pk=extracted.pk).exists():
                return
            HarvestSeasonCommodityFactory.create(harvest_season=extracted, commodity=commodity)
            return

        if commodity.harvest_seasons.exists():
            return

        HarvestSeasonCommodityFactory.create(commodity=commodity, harvest_season__commodity_group=commodity.group)


@pytest.fixture(autouse=True)
def reset_commodities_factories() -> None:
    CommodityGroupFactory.reset_sequence()
    CommodityFactory.reset_sequence()
