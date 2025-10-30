import factory
import pytest

from tests.factories.base import BaseFactory
from whimo.db.models import Balance


class BalanceFactory(BaseFactory[Balance]):
    class Meta:
        model = Balance

    commodity = factory.SubFactory("tests.factories.commodities.CommodityFactory")
    user = factory.SubFactory("tests.factories.users.UserFactory")
    volume = factory.Faker("pydecimal", min_value=1, max_value=1000, right_digits=2)


@pytest.fixture(autouse=True)
def reset_balances_factories() -> None:
    BalanceFactory.reset_sequence()
