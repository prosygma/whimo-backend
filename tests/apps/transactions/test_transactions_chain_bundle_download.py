import io
import json
import logging
import zipfile
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, FIXTURES_PATH
from whimo.db.enums import TransactionLocation, TransactionStatus, TransactionType
from whimo.db.models import Commodity, Transaction, User
from whimo.transactions.constants import LOCATION_S3_PREFIX

pytestmark = [pytest.mark.django_db]


class TestTransactionsChainBundleDownload:
    URL = "transactions_chain_bundle_download"

    def test_zip_contents_and_headers_values(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("merged.geojson", "{}")
            zf.writestr("11111111-1111-1111-1111-111111111111.geojson", "{}")
            zf.writestr("22222222-2222-2222-2222-222222222222.geojson", "{}")
        zip_bytes = buffer.getvalue()

        dto = SimpleNamespace(
            geojson_merged_transactions=["1", "2"],
            custom_location_file_transactions=["x"],
            no_location_file_transactions=["a", "b", "c"],
        )

        # Act
        with patch(
            "whimo.transactions.services.TransactionsService.get_chain_location_bundle",
            return_value=(zip_bytes, dto),
        ):
            response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "application/zip"
        assert response["X-Geojson-Merged-Transactions"] == "2"
        assert response["X-Custom-Location-File-Transactions"] == "1"
        assert response["X-No-Location-File-Transactions"] == "3"

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            file_list = set(zip_file.namelist())
            assert file_list == {
                "merged.geojson",
                "11111111-1111-1111-1111-111111111111.geojson",
                "22222222-2222-2222-2222-222222222222.geojson",
            }

    def test_empty_bundle_zip_and_headers(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("merged.geojson", "{}")
        zip_bytes = buffer.getvalue()

        dto = SimpleNamespace(
            geojson_merged_transactions=[],
            custom_location_file_transactions=[],
            no_location_file_transactions=[],
        )

        # Act
        with patch(
            "whimo.transactions.services.TransactionsService.get_chain_location_bundle",
            return_value=(zip_bytes, dto),
        ):
            response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["X-Geojson-Merged-Transactions"] == "0"
        assert response["X-Custom-Location-File-Transactions"] == "0"
        assert response["X-No-Location-File-Transactions"] == "0"

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            file_list = zip_file.namelist()
            assert file_list == ["merged.geojson"]

    def test_transaction_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        other_user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=other_user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response.json()

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        dummy_dto = SimpleNamespace(
            geojson_merged_transactions=[],
            custom_location_file_transactions=[],
            no_location_file_transactions=[],
        )

        # Act
        with patch(
            "whimo.transactions.services.TransactionsService.get_chain_location_bundle",
            return_value=(b"", dummy_dto),
        ):
            for _i in range(10):
                response = client.get(path=url)
                assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN]

            response = client.get(path=url)
            response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot


QR_GEOJSON = (FIXTURES_PATH / "location_file" / "geo.json").read_bytes()
QR_BARE_FEATURE = (FIXTURES_PATH / "location_file" / "feature.json").read_bytes()


def farm(buyer: User, commodity: Commodity, location: TransactionLocation | None, **kwargs: object) -> Transaction:
    coordinates = {
        "farm_latitude": None,
        "farm_longitude": None,
        "transaction_latitude": None,
        "transaction_longitude": None,
    }
    return TransactionFactory.create(
        producer=True,
        buyer=buyer,
        commodity=commodity,
        location=location,
        **{**coordinates, **kwargs},
    )


def trade(seller: User, buyer: User, commodity: Commodity) -> Transaction:
    return TransactionFactory.create(
        type=TransactionType.DOWNSTREAM,
        status=TransactionStatus.ACCEPTED,
        seller=seller,
        buyer=buyer,
        commodity=commodity,
        location=None,
    )


def stored_files(files: dict[Transaction, bytes]) -> MagicMock:
    contents = {f"{LOCATION_S3_PREFIX}/{transaction.id}": content for transaction, content in files.items()}

    def open_file(path: str) -> Mock:
        if path not in contents:
            raise FileNotFoundError(path)
        return Mock(read=Mock(return_value=contents[path]))

    return MagicMock(open=Mock(side_effect=open_file))


class TestChainBundleContents:
    URL = "transactions_chain_bundle_download"

    def test_farms_are_classified_by_location(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        gps_farm = farm(farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        file_farm = farm(farmer, commodity, TransactionLocation.FILE)
        manual_farm = farm(
            farmer, commodity, TransactionLocation.MANUAL, transaction_latitude=3, transaction_longitude=4
        )
        unlocated_farm = farm(farmer, commodity, None)

        trade(farmer, trader, commodity)
        root = trade(trader, user, commodity)

        client.login(user)

        # Act
        with patch(
            "whimo.transactions.services.default_storage",
            stored_files({qr_farm: QR_GEOJSON, file_farm: b"farm boundary"}),
        ):
            response = client.get(path=reverse(self.URL, args=(root.id,)))

        # Assert
        assert response.status_code == HTTPStatus.OK

        farms = [qr_farm, gps_farm, file_farm, manual_farm, unlocated_farm]
        counts = [
            int(response["X-Geojson-Merged-Transactions"]),
            int(response["X-Custom-Location-File-Transactions"]),
            int(response["X-No-Location-File-Transactions"]),
        ]
        assert counts == [2, 2, 1]
        assert sum(counts) == len(farms)

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            assert set(zip_file.namelist()) == {"merged.geojson", f"{qr_farm.id}.geojson", str(file_farm.id)}
            assert zip_file.read(str(file_farm.id)) == b"farm boundary"
            merged = json.loads(zip_file.read("merged.geojson"))

        geometries = {feature["properties"]["TransactionId"]: feature["geometry"] for feature in merged["features"]}
        assert geometries[str(qr_farm.id)]["type"] == "Polygon"
        assert geometries[str(gps_farm.id)] == {"type": "Point", "coordinates": [2.0, 1.0]}
        assert geometries[str(manual_farm.id)] == {"type": "Point", "coordinates": [4.0, 3.0]}
        assert str(file_farm.id) not in geometries

    def test_a_qr_file_holding_a_bare_feature_reaches_the_merged_geojson(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        root = trade(farmer, user, commodity)

        client.login(user)

        # Act
        with patch("whimo.transactions.services.default_storage", stored_files({qr_farm: QR_BARE_FEATURE})):
            response = client.get(path=reverse(self.URL, args=(root.id,)))

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["X-Geojson-Merged-Transactions"] == "1"

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            assert f"{qr_farm.id}.geojson" in zip_file.namelist()
            merged = json.loads(zip_file.read("merged.geojson"))

        assert [feature["properties"]["TransactionId"] for feature in merged["features"]] == [str(qr_farm.id)]

    def test_a_missing_or_invalid_file_keeps_the_farm_in_its_bucket(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        missing_qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        invalid_qr_farm = farm(farmer, commodity, TransactionLocation.QR)
        missing_file_farm = farm(farmer, commodity, TransactionLocation.FILE)

        root = trade(farmer, user, commodity)

        client.login(user)

        # Act
        with (
            caplog.at_level(logging.WARNING),
            patch(
                "whimo.transactions.services.default_storage",
                stored_files({invalid_qr_farm: b"not geojson"}),
            ),
        ):
            response = client.get(path=reverse(self.URL, args=(root.id,)))

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["X-Geojson-Merged-Transactions"] == "2"
        assert response["X-Custom-Location-File-Transactions"] == "1"
        assert response["X-No-Location-File-Transactions"] == "0"

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            assert zip_file.namelist() == ["merged.geojson"]
            assert json.loads(zip_file.read("merged.geojson"))["features"] == []

        for skipped in [missing_qr_farm, invalid_qr_farm, missing_file_farm]:
            assert str(skipped.id) in caplog.text

    def test_a_gps_farm_without_coordinates_is_still_counted(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user, farmer = UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        farm(farmer, commodity, TransactionLocation.GPS)
        root = trade(farmer, user, commodity)

        client.login(user)

        # Act
        with patch("whimo.transactions.services.default_storage", stored_files({})):
            response = client.get(path=reverse(self.URL, args=(root.id,)))

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["X-Geojson-Merged-Transactions"] == "1"

        with zipfile.ZipFile(io.BytesIO(response.content), "r") as zip_file:
            assert json.loads(zip_file.read("merged.geojson"))["features"] == []
