from decimal import Decimal
from uuid import UUID, uuid4

import factory
import pytest

from tests.factories.base import BaseFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonFactory
from whimo.db.enums import TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Transaction, User


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
    harvest_season = factory.LazyAttribute(lambda transaction: transaction.commodity.harvest_seasons.first())
    volume = factory.Faker("pydecimal", min_value=1, max_value=1000, right_digits=2)

    is_buying_from_farmer = False
    is_automatic = False
    expires_at = None

    seller = factory.SubFactory("tests.factories.users.UserFactory")
    buyer = factory.SubFactory("tests.factories.users.UserFactory")
    created_by = factory.LazyAttribute(lambda o: o.buyer if o.type == TransactionType.PRODUCER else o.seller)


def create_conversion(
    user: User,
    group_id: UUID | None,
    inputs: list[Decimal],
    outputs: list[Decimal],
) -> list[Transaction]:
    harvest_season = HarvestSeasonFactory.create()
    rows = [(-volume, user, None) for volume in inputs] + [(volume, None, user) for volume in outputs]

    return [
        TransactionFactory.create(
            type=TransactionType.CONVERSION,
            status=TransactionStatus.ACCEPTED,
            group_id=group_id,
            # A Faker-random code risks colliding with another commodity created earlier in the same
            # test; derive a short, collision-free one instead of relying on chance.
            commodity=CommodityFactory.create(
                with_harvest_season=harvest_season,
                code=f"{str(group_id or uuid4()).replace('-', '')[-12:]}-{row_index}",
            ),
            harvest_season=harvest_season,
            volume=volume,
            seller=seller,
            buyer=buyer,
            created_by=user,
        )
        for row_index, (volume, seller, buyer) in enumerate(rows)
    ]


@pytest.fixture(autouse=True)
def reset_transactions_factories() -> None:
    TransactionFactory.reset_sequence()
