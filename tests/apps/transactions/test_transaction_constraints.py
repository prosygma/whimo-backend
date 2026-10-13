import pytest
from django.db import IntegrityError
from django.db import transaction as db_transaction

from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory

pytestmark = [pytest.mark.django_db(transaction=True)]


class TestTransactionConstraints:
    def test_harvest_season_must_cover_the_commodity(self) -> None:
        # Arrange
        commodity = CommodityFactory.create()
        foreign_season = HarvestSeasonFactory.create()

        # Act & Assert
        with pytest.raises(IntegrityError), db_transaction.atomic():
            TransactionFactory.create(commodity=commodity, harvest_season=foreign_season)

    def test_harvest_season_covering_the_commodity_allowed(self) -> None:
        # Arrange
        commodity = CommodityFactory.create()

        # Act
        transaction = TransactionFactory.create(commodity=commodity)

        # Assert
        assert transaction.harvest_season in commodity.harvest_seasons.all()
