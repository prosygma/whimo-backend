from http import HTTPStatus
from unittest.mock import Mock, patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.analytics.constants import USER_ANALYTICS_CACHE_KEY
from whimo.analytics.schemas.dto import AnalyticsDataDTO, UserMetricsDTO
from whimo.common.schemas.base import DataResponse

pytestmark = [pytest.mark.django_db]


class TestAnalytics:
    URL = reverse("analytics")

    def test_success(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
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

        data_response = DataResponse[AnalyticsDataDTO](**response_json)
        assert data_response.data.active_traders is not None
        assert data_response.data.balance_summary is not None
        assert data_response.data.transactions_by_traceability is not None
        assert data_response.data.user_growth is not None
        assert data_response.data.current_seasons is not None
        assert data_response.data.season_transactions_daily is not None
        assert data_response.data.transactions_by_seasons is not None

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


class TestUserAnalytics:
    URL = reverse("user_analytics")

    def teardown_method(self) -> None:
        cache.clear()

    def test_success_no_transactions(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
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

        data_response = DataResponse[UserMetricsDTO](**response_json)
        assert data_response.data.total_transactions == 0
        assert data_response.data.total_suppliers == 0
        assert data_response.data.initial_plots == 0
        assert data_response.data.files_uploaded == 0

    @patch("whimo.analytics.services.default_storage.exists")
    def test_success_with_transactions(
        self,
        mock_storage_exists: Mock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        supplier1 = UserFactory.create()
        supplier2 = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            buyer=user,
            seller=supplier1,
            commodity=commodity,
            farm_latitude=10.123,
            farm_longitude=20.456,
        )
        TransactionFactory.create(
            buyer=user,
            seller=supplier2,
            commodity=commodity,
            farm_latitude=11.789,
            farm_longitude=21.987,
        )

        TransactionFactory.create(
            seller=user,
            buyer=supplier1,
            commodity=commodity,
            farm_latitude=12.345,
            farm_longitude=23.678,
        )

        TransactionFactory.create(
            created_by=user,
            commodity=commodity,
            farm_latitude=13.567,
            farm_longitude=24.890,
        )

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[UserMetricsDTO](**response_json)
        assert data_response.data.total_transactions == 4  # noqa: PLR2004
        assert data_response.data.total_suppliers == 2  # noqa: PLR2004
        assert data_response.data.initial_plots == 4  # noqa: PLR2004
        assert data_response.data.files_uploaded == 0

    def test_success_duplicate_plots(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        supplier = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            buyer=user,
            seller=supplier,
            commodity=commodity,
            farm_latitude=10.123,
            farm_longitude=20.456,
        )
        TransactionFactory.create(
            buyer=user,
            seller=supplier,
            commodity=commodity,
            farm_latitude=10.123,  # Same coordinates
            farm_longitude=20.456,
        )

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        data_response = DataResponse[UserMetricsDTO](**response_json)
        assert data_response.data.total_transactions == 2  # noqa: PLR2004
        assert data_response.data.initial_plots == 1

    @patch("whimo.analytics.services.default_storage.exists")
    def test_success_with_files(
        self,
        mock_storage_exists: Mock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        tx1 = TransactionFactory.create(created_by=user, commodity=commodity)
        tx2 = TransactionFactory.create(created_by=user, commodity=commodity)
        TransactionFactory.create(created_by=user, commodity=commodity)  # tx3

        def mock_exists(path: str) -> bool:
            return path.endswith((str(tx1.id), str(tx2.id)))

        mock_storage_exists.side_effect = mock_exists

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        data_response = DataResponse[UserMetricsDTO](**response_json)
        assert data_response.data.files_uploaded == 2  # noqa: PLR2004

    @patch("whimo.analytics.services.default_storage.exists")
    def test_caching(
        self,
        mock_storage_exists: Mock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(buyer=user, commodity=commodity)

        client.login(user)
        cache_key = USER_ANALYTICS_CACHE_KEY.format(user_id=user.id)

        cache.delete(cache_key)
        assert cache.get(cache_key) is None

        response1 = client.get(path=self.URL)
        response1_json = response1.json()

        assert response1.status_code == HTTPStatus.OK
        cached_data = cache.get(cache_key)
        assert cached_data is not None
        assert cached_data["total_transactions"] == 1

        response2 = client.get(path=self.URL)
        response2_json = response2.json()

        assert response2.status_code == HTTPStatus.OK
        assert response1_json == response2_json

    @patch("whimo.analytics.services.default_storage.exists")
    def test_cache_timeout(
        self,
        mock_storage_exists: Mock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        TransactionFactory.create(buyer=user, commodity=commodity)

        client.login(user)
        cache_key = USER_ANALYTICS_CACHE_KEY.format(user_id=user.id)

        response1 = client.get(path=self.URL)
        assert response1.status_code == HTTPStatus.OK
        assert cache.get(cache_key) is not None

        freezer.move_to(DEFAULT_DATETIME)
        freezer.tick(delta=3700)

        cache.delete(cache_key)
        assert cache.get(cache_key) is None

        client.login(user)
        response2 = client.get(path=self.URL)
        assert response2.status_code == HTTPStatus.OK
        assert cache.get(cache_key) is not None

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    @patch("whimo.analytics.services.default_storage.exists")
    def test_cache_isolation(
        self,
        mock_storage_exists: Mock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        mock_storage_exists.return_value = False
        freezer.move_to(DEFAULT_DATETIME)
        user1 = UserFactory.create()
        user2 = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(buyer=user1, commodity=commodity)
        TransactionFactory.create_batch(2, buyer=user2, commodity=commodity)

        client.login(user1)
        response1 = client.get(path=self.URL)
        user1_data = response1.json()

        client.login(user2)
        response2 = client.get(path=self.URL)
        user2_data = response2.json()

        assert response1.status_code == HTTPStatus.OK
        assert response2.status_code == HTTPStatus.OK
        assert user1_data["data"]["total_transactions"] == 1
        assert user2_data["data"]["total_transactions"] == 2  # noqa: PLR2004

        cache_key1 = USER_ANALYTICS_CACHE_KEY.format(user_id=user1.id)
        cache_key2 = USER_ANALYTICS_CACHE_KEY.format(user_id=user2.id)
        assert cache.get(cache_key1) is not None
        assert cache.get(cache_key2) is not None
        assert cache.get(cache_key1) != cache.get(cache_key2)
