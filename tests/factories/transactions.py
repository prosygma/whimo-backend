import factory
import pytest

from tests.factories.base import BaseFactory
from whimo.db.enums import TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Transaction


class TransactionFactory(BaseFactory[Transaction]):
    class Meta:
        model = Transaction

    class Params:
        producer = factory.Trait(
            seller=None,
            is_buying_from_farmer=True,
            type=TransactionType.PRODUCER,
            status=TransactionStatus.ACCEPTED,
        )

    type = factory.Faker("random_element", elements=TransactionType)
    location = factory.Faker("random_element", elements=TransactionLocation)
    status = factory.Faker("random_element", elements=TransactionStatus)
    traceability = factory.Faker("random_element", elements=TransactionTraceability)

    transaction_latitude = factory.Faker("pydecimal", min_value=-90, max_value=90, right_digits=2)
    transaction_longitude = factory.Faker("pydecimal", min_value=-180, max_value=180, right_digits=2)

    farm_latitude = factory.Faker("pydecimal", min_value=-90, max_value=90, right_digits=2)
    farm_longitude = factory.Faker("pydecimal", min_value=-180, max_value=180, right_digits=2)

    commodity = factory.SubFactory("tests.factories.commodities.CommodityFactory")
    volume = factory.Faker("pydecimal", min_value=1, max_value=1000, right_digits=2)

    is_buying_from_farmer = False
    is_automatic = False
    expires_at = None

    seller = factory.SubFactory("tests.factories.users.UserFactory")
    buyer = factory.SubFactory("tests.factories.users.UserFactory")
    created_by = factory.LazyAttribute(lambda o: o.buyer if o.type == TransactionType.PRODUCER else o.seller)


@pytest.fixture(autouse=True)
def reset_transactions_factories() -> None:
    TransactionFactory.reset_sequence()
