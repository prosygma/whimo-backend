import io
import json
import zipfile
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory

from tests.apps.transactions.test_transactions_chain_bundle_download import QR_GEOJSON, farm, stored_files, trade
from tests.factories.commodities import CommodityFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import TransactionLocation
from whimo.transactions.schemas.dto import LocationSummaryDTO

pytestmark = [pytest.mark.django_db]


class TestTransactionsListLocationDownload:
    BUNDLE_URL = reverse("transactions_list_bundle_download")
    SUMMARY_URL = reverse("transactions_list_summary")

    def test_summary_matches_the_bundle(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity, other_commodity = CommodityFactory.create(), CommodityFactory.create()

        qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        farm(farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        file_farm = farm(trader, other_commodity, TransactionLocation.FILE)
        farm(farmer, commodity, None)

        trade(farmer, trader, commodity)
        trade(trader, user, commodity)
        trade(trader, user, other_commodity)

        client.login(user)
        storage = stored_files({qr_farm: QR_GEOJSON, file_farm: b"farm boundary"})

        # Act
        with patch("whimo.transactions.services.default_storage", storage):
            bundle_response = client.get(path=self.BUNDLE_URL)
            summary_response = client.get(path=self.SUMMARY_URL)

        # Assert
        assert bundle_response.status_code == HTTPStatus.OK
        assert summary_response.status_code == HTTPStatus.OK

        summary = DataResponse[LocationSummaryDTO](**summary_response.json()).data
        assert summary.full_traceability_farms == int(bundle_response["X-Geojson-Merged-Transactions"]) == 2  # noqa: PLR2004 Magic value used in comparison
        assert summary.manually_added_farms == int(bundle_response["X-Custom-Location-File-Transactions"]) == 1
        assert summary.farms_without_geolocation == int(bundle_response["X-No-Location-File-Transactions"]) == 1
        assert summary.traders == 1

        with zipfile.ZipFile(io.BytesIO(bundle_response.content), "r") as zip_file:
            assert set(zip_file.namelist()) == {"merged.geojson", f"{qr_farm.id}.geojson", str(file_farm.id)}
            assert len(json.loads(zip_file.read("merged.geojson"))["features"]) == 2  # noqa: PLR2004 Magic value used in comparison

    def test_a_farm_behind_two_transactions_is_counted_once(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        trade(farmer, trader, commodity)
        trade(trader, user, commodity)
        trade(trader, user, commodity)

        client.login(user)

        # Act
        with patch("whimo.transactions.services.default_storage", stored_files({qr_farm: QR_GEOJSON})):
            bundle_response = client.get(path=self.BUNDLE_URL)
            summary_response = client.get(path=self.SUMMARY_URL)

        # Assert
        summary = DataResponse[LocationSummaryDTO](**summary_response.json()).data
        assert summary.full_traceability_farms == 1
        assert bundle_response["X-Geojson-Merged-Transactions"] == "1"

        with zipfile.ZipFile(io.BytesIO(bundle_response.content), "r") as zip_file:
            assert zip_file.namelist().count(f"{qr_farm.id}.geojson") == 1
            assert len(json.loads(zip_file.read("merged.geojson"))["features"]) == 1

    def test_filters_narrow_the_farms(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity, other_commodity = CommodityFactory.create(), CommodityFactory.create()

        farm(farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        farm(farmer, other_commodity, TransactionLocation.GPS, farm_latitude=3, farm_longitude=4)
        trade(farmer, user, commodity)
        trade(farmer, user, other_commodity)

        client.login(user)

        # Act
        with patch("whimo.transactions.services.default_storage", stored_files({})):
            response = client.get(path=f"{self.SUMMARY_URL}?commodity_id={commodity.id}")

        # Assert
        assert response.status_code == HTTPStatus.OK

        summary = DataResponse[LocationSummaryDTO](**response.json()).data
        assert summary.full_traceability_farms == 1
        assert summary.traders == 1

    def test_summary_reads_no_stored_file(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        farm(farmer, commodity, TransactionLocation.QR)
        trade(farmer, user, commodity)

        client.login(user)
        storage = stored_files({})

        # Act
        with patch("whimo.transactions.services.default_storage", storage):
            response = client.get(path=self.SUMMARY_URL)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert DataResponse[LocationSummaryDTO](**response.json()).data.full_traceability_farms == 1
        storage.open.assert_not_called()

    def test_query_count_follows_chain_depth_not_transaction_count(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        farm(farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        trade(farmer, user, commodity)

        client.login(user)

        with CaptureQueriesContext(connection) as single_queries:
            client.get(path=self.SUMMARY_URL)

        for _ in range(MEDIUM_BATCH_SIZE):
            other_farmer = UserFactory.create()
            farm(other_farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
            trade(other_farmer, user, commodity)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.SUMMARY_URL)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert DataResponse[LocationSummaryDTO](**response.json()).data.full_traceability_farms == MEDIUM_BATCH_SIZE + 1
        assert len(queries) == len(single_queries), queries_to_str(queries)

    def test_every_root_keeps_its_own_cutoff(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, early_farmer, late_farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        early_commodity, late_commodity = CommodityFactory.create(), CommodityFactory.create()

        farm(early_farmer, early_commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        trade(early_farmer, user, early_commodity)

        freezer.move_to(DEFAULT_DATETIME.replace(year=2021))
        # Created after the early root was last updated, so its own chain no longer
        # reaches it - a single cutoff shared by both roots would pull it in.
        farm(early_farmer, early_commodity, TransactionLocation.GPS, farm_latitude=3, farm_longitude=4)
        farm(late_farmer, late_commodity, TransactionLocation.GPS, farm_latitude=5, farm_longitude=6)
        trade(late_farmer, user, late_commodity)

        client.login(user)

        # Act
        with patch("whimo.transactions.services.default_storage", stored_files({})):
            response = client.get(path=self.SUMMARY_URL)

        # Assert
        assert response.status_code == HTTPStatus.OK

        summary = DataResponse[LocationSummaryDTO](**response.json()).data
        assert summary.full_traceability_farms == 2  # noqa: PLR2004 Magic value used in comparison
        assert summary.traders == 2  # noqa: PLR2004 Magic value used in comparison
