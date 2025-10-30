import factory
import pytest

from tests.factories.base import BaseFactory
from whimo.db.models import Commodity, CommodityGroup


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


@pytest.fixture(autouse=True)
def reset_commodities_factories() -> None:
    CommodityGroupFactory.reset_sequence()
    CommodityFactory.reset_sequence()
