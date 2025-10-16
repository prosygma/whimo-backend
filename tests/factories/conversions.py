import factory
import pytest

from tests.factories.base import BaseFactory
from tests.factories.commodities import CommodityFactory
from whimo.db.models import ConversionInput, ConversionOutput, ConversionRecipe


class ConversionRecipeFactory(BaseFactory[ConversionRecipe]):
    class Meta:
        model = ConversionRecipe

    name = factory.Faker("sentence", nb_words=3)


class ConversionInputFactory(BaseFactory[ConversionInput]):
    class Meta:
        model = ConversionInput

    recipe = factory.SubFactory(ConversionRecipeFactory)
    commodity = factory.SubFactory(CommodityFactory)
    quantity = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)


class ConversionOutputFactory(BaseFactory[ConversionOutput]):
    class Meta:
        model = ConversionOutput

    recipe = factory.SubFactory(ConversionRecipeFactory)
    commodity = factory.SubFactory(CommodityFactory)
    quantity = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True)


@pytest.fixture(autouse=True)
def reset_conversions_factories() -> None:
    ConversionRecipeFactory.reset_sequence()
    ConversionInputFactory.reset_sequence()
    ConversionOutputFactory.reset_sequence()
