from datetime import date
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import HarvestSeasonStatus, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Commodity, HarvestSeason, Transaction
from whimo.transactions.schemas.dto import TraceabilityCountsDTO

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def commodity() -> Commodity:
    return CommodityFactory.create(with_harvest_season=False)


@pytest.fixture
def past_season(commodity: Commodity) -> HarvestSeason:
    season = HarvestSeasonFactory.create(
        start_date=date(2024, 9, 1),
        end_date=date(2025, 9, 1),
        status=HarvestSeasonStatus.PAST,
    )
    HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)
    return season


@pytest.fixture
def active_season(commodity: Commodity) -> HarvestSeason:
    season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
    HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodity)
    return season


class TestSeasonScopedTraceability:
    STATUS_URL = "transactions_status_update"
    COUNTS_URL = "transactions_traceability_counts"

    def test_poor_history_of_one_season_does_not_reach_another(
        self,
        client: APIClient,
        commodity: Commodity,
        past_season: HarvestSeason,
        active_season: HarvestSeason,
    ) -> None:
        # Arrange
        buyer = UserFactory.create()
        seller = UserFactory.create()

        TransactionFactory.create(
            producer=True,
            buyer=seller,
            commodity=commodity,
            harvest_season=past_season,
            traceability=TransactionTraceability.INCOMPLETE,
        )
        TransactionFactory.create(
            producer=True,
            buyer=seller,
            commodity=commodity,
            harvest_season=active_season,
            traceability=TransactionTraceability.FULL,
        )

        transaction = TransactionFactory.create(
            buyer=buyer,
            seller=seller,
            created_by=buyer,
            commodity=commodity,
            harvest_season=active_season,
            volume=Decimal("10.0"),
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )
        BalanceFactory.create(
            user=seller,
            commodity=commodity,
            harvest_season=active_season,
            volume=Decimal("50.0"),
        )

        client.login(seller)

        # Act
        response = client.patch(
            path=reverse(self.STATUS_URL, args=(transaction.id,)),
            data={"status": TransactionStatus.ACCEPTED},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK, response.json()

        transaction.refresh_from_db()
        assert transaction.traceability == TransactionTraceability.FULL

    def test_chain_stops_at_the_season_boundary(
        self,
        client: APIClient,
        commodity: Commodity,
        past_season: HarvestSeason,
        active_season: HarvestSeason,
    ) -> None:
        # Arrange
        buyer = UserFactory.create()
        seller = UserFactory.create()
        farmer = UserFactory.create()

        TransactionFactory.create(
            buyer=seller,
            seller=farmer,
            created_by=farmer,
            commodity=commodity,
            harvest_season=active_season,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.FULL,
        )
        TransactionFactory.create(
            buyer=seller,
            seller=farmer,
            created_by=farmer,
            commodity=commodity,
            harvest_season=past_season,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.INCOMPLETE,
        )

        transaction = TransactionFactory.create(
            buyer=buyer,
            seller=seller,
            created_by=seller,
            commodity=commodity,
            harvest_season=active_season,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.ACCEPTED,
            traceability=TransactionTraceability.FULL,
        )

        client.login(buyer)

        # Act
        response = client.get(path=reverse(self.COUNTS_URL, args=(transaction.id,)))
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        counts = DataResponse[TraceabilityCountsDTO](**response_json).data.counts
        assert counts[TransactionTraceability.FULL] == 2  # noqa: PLR2004 Magic value used in comparison
        assert counts[TransactionTraceability.INCOMPLETE] == 0

    def test_conversion_inherits_only_its_own_season(
        self,
        client: APIClient,
        commodity: Commodity,
        past_season: HarvestSeason,
        active_season: HarvestSeason,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        output_commodity = CommodityFactory.create(with_harvest_season=False)
        HarvestSeasonCommodityFactory.create(harvest_season=past_season, commodity=output_commodity)
        HarvestSeasonCommodityFactory.create(harvest_season=active_season, commodity=output_commodity)

        TransactionFactory.create(
            producer=True,
            buyer=user,
            commodity=commodity,
            harvest_season=active_season,
            traceability=TransactionTraceability.FULL,
        )
        TransactionFactory.create(
            producer=True,
            buyer=user,
            commodity=commodity,
            harvest_season=past_season,
            traceability=TransactionTraceability.INCOMPLETE,
        )

        recipe = ConversionRecipeFactory.create(name="Season bound recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=commodity, harvest_season=active_season, volume=Decimal("20.0"))

        client.login(user)

        # Act
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe.id), "harvest_season_id": str(active_season.id)},
            format="json",
        )

        # Assert
        assert response.status_code == HTTPStatus.OK, response.json()

        conversions = Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION)
        assert {conversion.harvest_season_id for conversion in conversions} == {active_season.id}
        assert {conversion.traceability for conversion in conversions} == {TransactionTraceability.FULL}

    def test_conversion_takes_the_worst_status_of_its_inputs(
        self,
        client: APIClient,
        commodity: Commodity,
        active_season: HarvestSeason,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        second_input = CommodityFactory.create(with_harvest_season=active_season)
        output_commodity = CommodityFactory.create(with_harvest_season=active_season)

        recipe = ConversionRecipeFactory.create(name="Two input recipe")
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))
        for input_commodity, traceability in (
            (commodity, TransactionTraceability.FULL),
            (second_input, TransactionTraceability.CONDITIONAL),
        ):
            ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
            TransactionFactory.create(
                producer=True,
                buyer=user,
                commodity=input_commodity,
                harvest_season=active_season,
                traceability=traceability,
            )
            BalanceFactory.create(
                user=user,
                commodity=input_commodity,
                harvest_season=active_season,
                volume=Decimal("20.0"),
            )

        client.login(user)

        # Act
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe.id), "harvest_season_id": str(active_season.id)},
            format="json",
        )

        # Assert
        assert response.status_code == HTTPStatus.OK, response.json()

        conversions = Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION)
        assert {conversion.traceability for conversion in conversions} == {TransactionTraceability.CONDITIONAL}
