import math
from http import HTTPStatus

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.commodities.schemas.dto import (
    CommodityGroupWithCommoditiesBalancesDTO,
)
from whimo.common.schemas.base import PaginatedDataResponse

pytestmark = [pytest.mark.django_db]


class TestCommoditiesGroupsList:
    URL = reverse("commodities_groups_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        groups = CommodityGroupFactory.create_batch(size=SMALL_BATCH_SIZE)
        commodities = CommodityFactory.create_batch(size=SMALL_BATCH_SIZE, group=groups[0])
        balances = BalanceFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            user=user,
            commodity=factory.Iterator(commodities),
        )

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityGroupWithCommoditiesBalancesDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

        group_ids = {group.id for group in groups}
        response_group_ids = {group.id for group in data_response.data}
        assert response_group_ids == group_ids

        commodity_ids = {commodity.id for commodity in commodities}
        response_commodity_ids = {commodity.id for commodity in data_response.data[0].commodities}
        assert response_commodity_ids == commodity_ids

        response_balance_volumes = {commodity.balance for commodity in data_response.data[0].commodities}
        assert response_balance_volumes == {balance.volume for balance in balances}

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        # 5. prefetch related entities
        assert len(queries) == 5, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        group = CommodityGroupFactory.create()
        CommodityGroupFactory.create_batch(size=SMALL_BATCH_SIZE, name=factory.Faker("numerify", text="####"))

        search_term = group.name[:3]

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityGroupWithCommoditiesBalancesDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == group.id

    @pytest.mark.parametrize(("page", "page_size"), [(1, 2), (2, 2)])
    def test_pagination(
        self,
        page: int,
        page_size: int,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        CommodityGroupFactory.create_batch(size=MEDIUM_BATCH_SIZE)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityGroupWithCommoditiesBalancesDTO]](**response_json)
        assert data_response.pagination.page == page
        assert data_response.pagination.page_size == page_size
        assert data_response.pagination.count == MEDIUM_BATCH_SIZE

        expected_total_pages = math.ceil(MEDIUM_BATCH_SIZE / page_size)
        assert data_response.pagination.total_pages == expected_total_pages

        remaining_items = max(0, MEDIUM_BATCH_SIZE - (page - 1) * page_size)
        expected_items_count = min(page_size, remaining_items)
        assert len(data_response.data) == expected_items_count

    def test_empty_result(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityGroupWithCommoditiesBalancesDTO]](**response_json)
        assert len(data_response.data) == 0
        assert data_response.pagination.count == 0

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
