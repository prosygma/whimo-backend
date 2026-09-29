import pytest
from django.db import IntegrityError

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonFactory
from tests.factories.users import UserFactory
from tests.helpers.constants import SMALL_BATCH_SIZE
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import Balance

pytestmark = [pytest.mark.django_db(transaction=True)]


class TestBalanceConstraints:
    def test_second_balance_over_same_commodity_and_season_rejected(self) -> None:
        # Arrange
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        harvest_season = HarvestSeasonFactory.create()
        BalanceFactory.create(user=user, commodity=commodity, harvest_season=harvest_season)

        # Act & Assert
        with pytest.raises(IntegrityError):
            BalanceFactory.create(user=user, commodity=commodity, harvest_season=harvest_season)

    def test_same_commodity_in_another_season_allowed(self) -> None:
        # Arrange
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        past_season = HarvestSeasonFactory.create(status=HarvestSeasonStatus.PAST)

        # Act
        BalanceFactory.create(user=user, commodity=commodity)
        BalanceFactory.create(user=user, commodity=commodity, harvest_season=past_season)

        # Assert
        assert Balance.objects.filter(user=user, commodity=commodity).count() == SMALL_BATCH_SIZE
