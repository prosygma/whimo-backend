import math
from http import HTTPStatus

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.commodities.mappers.commodities import CommoditiesMapper
from whimo.commodities.schemas.dto import CommodityDTO, CommodityWithGroupDTO
from whimo.common.schemas.base import PaginatedDataResponse

pytestmark = [pytest.mark.django_db]


class TestCommoditiesList:
    URL = reverse("commodities_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        CommodityFactory.create_batch(size=SMALL_BATCH_SIZE)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()
        CommodityFactory.create_batch(size=SMALL_BATCH_SIZE, name=factory.Faker("numerify", text="####"))

        search_term = commodity.name[:3]

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == commodity.id

    def test_search_by_code(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()
        CommodityFactory.create_batch(size=SMALL_BATCH_SIZE)

        search_term = commodity.code[:3]

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == commodity.id

    def test_filter_by_group_id(
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
        CommodityFactory.create_batch(size=SMALL_BATCH_SIZE)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?group_id={group.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == commodity.id
        assert data_response.data[0].group.id == group.id

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
        CommodityFactory.create_batch(size=MEDIUM_BATCH_SIZE)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
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

        data_response = PaginatedDataResponse[list[CommodityWithGroupDTO]](**response_json)
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

    def test_basic_mapper(
        self, client: APIClient, mocker: MockerFixture, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodities = CommodityFactory.create_batch(size=2)

        def mock_basic_mapping(items: list) -> list:
            return CommoditiesMapper.to_dto_list(items)

        mocker.patch.object(CommoditiesMapper, "to_dto_list_with_group", side_effect=mock_basic_mapping)

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[CommodityDTO]](**response_json)
        assert len(data_response.data) == len(commodities)
