from datetime import date
from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.db.enums import HarvestSeasonStatus
from whimo.harvest_seasons.schemas.dto import HarvestSeasonDTO

pytestmark = [pytest.mark.django_db]


class TestHarvestSeasonsList:
    URL = reverse("harvest_seasons_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        HarvestSeasonFactory.create(
            start_date=date(2024, 9, 1),
            end_date=date(2025, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE
        assert [item.start_date for item in data_response.data] == [date(2025, 9, 1), date(2024, 9, 1)]

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_commodity_set_is_not_exposed(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        commodity = CommodityFactory.create(with_harvest_season=False)
        harvest_season = HarvestSeasonFactory.create()
        HarvestSeasonCommodityFactory.create(harvest_season=harvest_season, commodity=commodity)

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert set(response_json["data"][0]) == {"id", "name", "start_date", "end_date", "status"}

    def test_filter_by_single_commodity(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        cocoa = CommodityFactory.create(with_harvest_season=False)
        coffee = CommodityFactory.create(with_harvest_season=False)
        cocoa_season = HarvestSeasonFactory.create()
        coffee_season = HarvestSeasonFactory.create()
        HarvestSeasonCommodityFactory.create(harvest_season=cocoa_season, commodity=cocoa)
        HarvestSeasonCommodityFactory.create(harvest_season=coffee_season, commodity=coffee)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_id={cocoa.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert [item.id for item in data_response.data] == [cocoa_season.id]

    def test_filter_returns_seasons_covering_every_commodity(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        beans = CommodityFactory.create(with_harvest_season=False)
        butter = CommodityFactory.create(with_harvest_season=False)
        recipe_season = HarvestSeasonFactory.create()
        beans_only_season = HarvestSeasonFactory.create()

        HarvestSeasonCommodityFactory.create(harvest_season=recipe_season, commodity=beans)
        HarvestSeasonCommodityFactory.create(harvest_season=recipe_season, commodity=butter)
        HarvestSeasonCommodityFactory.create(
            harvest_season=beans_only_season,
            commodity=CommodityFactory.create(with_harvest_season=False),
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_id={beans.id}&commodity_id={butter.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert [item.id for item in data_response.data] == [recipe_season.id]
        assert beans_only_season.id not in [item.id for item in data_response.data]

    def test_filter_by_commodity_group(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        coffee_group = CommodityGroupFactory.create()
        green_beans = CommodityFactory.create(group=coffee_group, with_harvest_season=False)
        roasted = CommodityFactory.create(group=coffee_group, with_harvest_season=False)
        cocoa = CommodityFactory.create(with_harvest_season=False)

        coffee_season = HarvestSeasonFactory.create()
        cocoa_season = HarvestSeasonFactory.create()

        HarvestSeasonCommodityFactory.create(harvest_season=coffee_season, commodity=green_beans)
        HarvestSeasonCommodityFactory.create(harvest_season=cocoa_season, commodity=cocoa)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_group_id={coffee_group.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert [item.id for item in data_response.data] == [coffee_season.id]
        assert set(coffee_season.commodities.all()) == {green_beans, roasted}

    def test_season_of_several_group_commodities_is_returned_once(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        coffee_group = CommodityGroupFactory.create()
        season = HarvestSeasonFactory.create()
        commodities = CommodityFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            group=coffee_group,
            with_harvest_season=False,
        )
        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodities[0])

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_group_id={coffee_group.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert [item.id for item in data_response.data] == [season.id]
        assert data_response.pagination.count == 1

    def test_filter_by_status(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        active = HarvestSeasonFactory.create()
        HarvestSeasonFactory.create(
            start_date=date(2024, 9, 1),
            end_date=date(2025, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?status={HarvestSeasonStatus.ACTIVE.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert [item.id for item in data_response.data] == [active.id]

    def test_active_status_returns_a_season_per_commodity_set(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        cocoa_season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        coffee_season = HarvestSeasonFactory.create(start_date=date(2026, 3, 1), end_date=date(2027, 3, 1))
        HarvestSeasonCommodityFactory.create(
            harvest_season=cocoa_season, commodity=CommodityFactory.create(with_harvest_season=False)
        )
        HarvestSeasonCommodityFactory.create(
            harvest_season=coffee_season, commodity=CommodityFactory.create(with_harvest_season=False)
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?status={HarvestSeasonStatus.ACTIVE.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[HarvestSeasonDTO]](**response_json)
        assert {item.id for item in data_response.data} == {cocoa_season.id, coffee_season.id}

    def test_broken_configuration_never_conflicts(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        commodity = CommodityFactory.create(with_harvest_season=False)
        HarvestSeasonCommodityFactory.create(
            harvest_season=HarvestSeasonFactory.create(status=HarvestSeasonStatus.PAST),
            commodity=commodity,
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_id={commodity.id}&status={HarvestSeasonStatus.ACTIVE.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json["data"] == []

    def test_unauthorized(self, client: APIClient) -> None:
        # Act
        response = client.get(path=self.URL)

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response.json()
