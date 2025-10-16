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
from tests.factories.conversions import ConversionInputFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.commodities.schemas.dto import BalanceDTO
from whimo.common.schemas.base import PaginatedDataResponse

pytestmark = [pytest.mark.django_db]


class TestCommoditiesBalancesList:
    URL = reverse("commodities_balances_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        balances = BalanceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)
        BalanceFactory.create_batch(size=SMALL_BATCH_SIZE)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

        balance_ids = {balance.id for balance in balances}
        response_balance_ids = {balance.id for balance in data_response.data}
        assert response_balance_ids == balance_ids

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities (with has_recipe annotation)
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison  # noqa: PLR2004 Magic value used in comparison  # noqa: PLR2004 Magic value used in comparison  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_commodity_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        balance = BalanceFactory.create(user=user)
        search_term = balance.commodity.name[:3]
        BalanceFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            user=user,
            commodity__name=factory.Faker("numerify", text="####"),
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].commodity.id == balance.commodity.id

    def test_search_by_commodity_code(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        balance = BalanceFactory.create(user=user)
        search_term = balance.commodity.code[:3]
        BalanceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].commodity.id == balance.commodity.id

    def test_filter_by_commodity_group(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        group = CommodityGroupFactory.create()
        commodity = CommodityFactory.create(group=group)
        balance = BalanceFactory.create(user=user, commodity=commodity)
        BalanceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_group_id={group.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == balance.id
        assert data_response.data[0].commodity.group.id == group.id

    def test_filter_by_commodity_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()
        balance = BalanceFactory.create(user=user, commodity=commodity)
        BalanceFactory.create_batch(size=SMALL_BATCH_SIZE, user=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_id={commodity.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == balance.id
        assert data_response.data[0].commodity.id == commodity.id

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
        BalanceFactory.create_batch(size=MEDIUM_BATCH_SIZE, user=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert data_response.pagination.page == page
        assert data_response.pagination.page_size == page_size
        assert data_response.pagination.count == MEDIUM_BATCH_SIZE

        expected_total_pages = math.ceil(MEDIUM_BATCH_SIZE / page_size)
        assert data_response.pagination.total_pages == expected_total_pages

        remaining_items = max(0, MEDIUM_BATCH_SIZE - (page - 1) * page_size)
        expected_items_count = min(page_size, remaining_items)
        assert len(data_response.data) == expected_items_count

    def test_order_by_commodity_name_asc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        BalanceFactory.create(user=user, commodity__name="Banana")
        BalanceFactory.create(user=user, commodity__name="Apple")
        BalanceFactory.create(user=user, commodity__name="Cherry")

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=commodity_name")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].commodity.name == "Apple"
        assert data_response.data[1].commodity.name == "Banana"
        assert data_response.data[2].commodity.name == "Cherry"

    def test_order_by_commodity_name_desc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        BalanceFactory.create(user=user, commodity__name="Banana")
        BalanceFactory.create(user=user, commodity__name="Apple")
        BalanceFactory.create(user=user, commodity__name="Cherry")

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=-commodity_name")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].commodity.name == "Cherry"
        assert data_response.data[1].commodity.name == "Banana"
        assert data_response.data[2].commodity.name == "Apple"

    def test_order_by_amount_asc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        BalanceFactory.create(user=user, volume=50)
        BalanceFactory.create(user=user, volume=10)
        BalanceFactory.create(user=user, volume=30)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=amount")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].volume == 10  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[1].volume == 30  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[2].volume == 50  # noqa: PLR2004 Magic value used in comparison

    def test_order_by_amount_desc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        BalanceFactory.create(user=user, volume=50)
        BalanceFactory.create(user=user, volume=10)
        BalanceFactory.create(user=user, volume=30)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=-amount")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].volume == 50  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[1].volume == 30  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[2].volume == 10  # noqa: PLR2004 Magic value used in comparison

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

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 0
        assert data_response.pagination.count == 0

    def test_has_recipe_field(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()

        commodity_with_recipe = CommodityFactory.create()
        commodity_without_recipe = CommodityFactory.create()

        ConversionInputFactory.create(commodity=commodity_with_recipe)

        balance_with_recipe = BalanceFactory.create(user=user, commodity=commodity_with_recipe)
        balance_without_recipe = BalanceFactory.create(user=user, commodity=commodity_without_recipe)

        client.login(user)

        response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[BalanceDTO]](**response_json)
        assert len(data_response.data) == 2  # noqa: PLR2004 Magic value used in comparison

        balance_dict = {b.id: b for b in data_response.data}
        assert balance_dict[balance_with_recipe.id].has_recipe is True
        assert balance_dict[balance_without_recipe.id].has_recipe is False

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
