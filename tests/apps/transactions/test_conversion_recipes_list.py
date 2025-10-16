import math
from http import HTTPStatus

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.transactions.schemas.dto import ConversionRecipeDTO

pytestmark = [pytest.mark.django_db]


class TestConversionRecipesList:
    URL = reverse("transactions_conversion")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipes = ConversionRecipeFactory.create_batch(size=SMALL_BATCH_SIZE)
        for recipe in recipes:
            ConversionInputFactory.create_batch(size=2, recipe=recipe)
            ConversionOutputFactory.create_batch(size=2, recipe=recipe)

        client.login(user)

        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[ConversionRecipeDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        # 5. prefetch inputs with commodity and group
        # 6. prefetch outputs with commodity and group
        assert len(queries) == 6, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipe = ConversionRecipeFactory.create(name="Cocoa Processing Recipe")
        ConversionInputFactory.create(recipe=recipe)
        ConversionOutputFactory.create(recipe=recipe)

        other_recipes = ConversionRecipeFactory.create_batch(
            size=SMALL_BATCH_SIZE, name=factory.Faker("numerify", text="Recipe ####")
        )
        for r in other_recipes:
            ConversionInputFactory.create(recipe=r)
            ConversionOutputFactory.create(recipe=r)

        search_term = "Cocoa"

        client.login(user)

        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[ConversionRecipeDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == recipe.id

    def test_filter_by_commodity_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipe_with_commodity = ConversionRecipeFactory.create()
        conversion_input = ConversionInputFactory.create(recipe=recipe_with_commodity)
        ConversionOutputFactory.create(recipe=recipe_with_commodity)

        other_recipes = ConversionRecipeFactory.create_batch(size=SMALL_BATCH_SIZE)
        for r in other_recipes:
            ConversionInputFactory.create(recipe=r)
            ConversionOutputFactory.create(recipe=r)

        commodity_id = conversion_input.commodity_id

        client.login(user)

        response = client.get(path=f"{self.URL}?commodity_id={commodity_id}")
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[ConversionRecipeDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == recipe_with_commodity.id

    @pytest.mark.parametrize(("page", "page_size"), [(1, 2), (2, 2)])
    def test_pagination(
        self,
        page: int,
        page_size: int,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipes = ConversionRecipeFactory.create_batch(size=MEDIUM_BATCH_SIZE)
        for recipe in recipes:
            ConversionInputFactory.create(recipe=recipe)
            ConversionOutputFactory.create(recipe=recipe)

        client.login(user)

        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[ConversionRecipeDTO]](**response_json)
        assert data_response.pagination.page == page
        assert data_response.pagination.page_size == page_size
        assert data_response.pagination.count == MEDIUM_BATCH_SIZE

        expected_total_pages = math.ceil(MEDIUM_BATCH_SIZE / page_size)
        assert data_response.pagination.total_pages == expected_total_pages

        remaining_items = max(0, MEDIUM_BATCH_SIZE - (page - 1) * page_size)
        expected_items_count = min(page_size, remaining_items)
        assert len(data_response.data) == expected_items_count

    def test_empty_result(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        client.login(user)

        response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[ConversionRecipeDTO]](**response_json)
        assert len(data_response.data) == 0
        assert data_response.pagination.count == 0

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        response = client.get(path=self.URL)
        response_json = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
