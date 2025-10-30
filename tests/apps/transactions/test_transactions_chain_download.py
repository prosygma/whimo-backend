import json
import zipfile
from decimal import Decimal
from http import HTTPStatus
from io import BytesIO
from typing import Any, Never
from unittest.mock import MagicMock, Mock, patch
from uuid import UUID

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from pydantic import ValidationError
from pydantic_core import InitErrorDetails
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.common.schemas.base import DataResponse
from whimo.common.schemas.errors import NotFound
from whimo.db.enums import TransactionLocation
from whimo.db.models import Transaction
from whimo.transactions.schemas.dto import (
    ChainFeatureCollectionDTO,
    Feature,
    FeatureCollection,
    FeatureGeometry,
    FeatureProperties,
)
from whimo.transactions.schemas.errors import LocationFileDownloadError
from whimo.transactions.services import TransactionsService

pytestmark = [pytest.mark.django_db]


class TestTransactionsChainDownload:
    URL = "transactions_chain_download"

    def test_success_with_feature_collection(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        mock_feature_collection = FeatureCollection(
            type="FeatureCollection",
            features=[
                Feature(
                    type="Feature",
                    geometry=FeatureGeometry(
                        type="Polygon",
                        coordinates=[[[Decimal("-122.4194"), Decimal("37.7749"), Decimal("0")]]],
                    ),
                    properties=FeatureProperties(
                        ProducerName="Test Producer",
                        ProducerCountry="Test Country",
                        ProductionPlace="Test Place",
                        TransactionId="aaaaaaaa-4321-8765-cba9-987654321098",
                    ),
                )
            ],
        )
        mock_succeed_transactions: list[UUID] = [
            UUID("aaaaaaaa-4321-8765-cba9-987654321098"),
        ]
        mock_failed_transactions: list[UUID] = [
            UUID("12345678-1234-5678-9abc-123456789abc"),
            UUID("87654321-4321-8765-cba9-987654321098"),
        ]

        mock_get_chain_feature_collection.return_value = (
            mock_feature_collection,
            mock_succeed_transactions,
            mock_failed_transactions,
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[ChainFeatureCollectionDTO](**response_json)

        assert len(data_response.data.feature_collection.features) == 1
        assert len(data_response.data.succeed_transactions) == len(mock_succeed_transactions)
        assert len(data_response.data.failed_transactions) == len(mock_failed_transactions)

        mock_get_chain_feature_collection.assert_called_once_with(transaction_id=transaction.id)

    def test_seller_access(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(seller=user)

        mock_feature_collection = FeatureCollection(
            type="FeatureCollection",
            features=[
                Feature(
                    type="Feature",
                    geometry=FeatureGeometry(
                        type="Polygon",
                        coordinates=[[[Decimal("-122.4194"), Decimal("37.7749"), Decimal("0")]]],
                    ),
                    properties=FeatureProperties(
                        ProducerName="Test Seller",
                        ProducerCountry="Test Country",
                        ProductionPlace="Test Place",
                        TransactionId="12345678-1234-5678-9abc-123456789def",
                    ),
                )
            ],
        )
        mock_succeed_transactions: list[UUID] = []
        mock_failed_transactions: list[UUID] = []

        mock_get_chain_feature_collection.return_value = (
            mock_feature_collection,
            mock_succeed_transactions,
            mock_failed_transactions,
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[ChainFeatureCollectionDTO](**response_json)

        assert data_response.data.feature_collection.type == "FeatureCollection"
        assert len(data_response.data.feature_collection.features) == 1
        assert len(data_response.data.succeed_transactions) == 0
        assert len(data_response.data.failed_transactions) == 0

        mock_get_chain_feature_collection.assert_called_once_with(transaction_id=transaction.id)

    def test_success_empty_feature_collection(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        mock_feature_collection = FeatureCollection(type="FeatureCollection", features=[])
        mock_succeed_transactions: list[UUID] = []
        mock_failed_transactions: list[UUID] = []

        mock_get_chain_feature_collection.return_value = (
            mock_feature_collection,
            mock_succeed_transactions,
            mock_failed_transactions,
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[ChainFeatureCollectionDTO](**response_json)

        assert data_response.data.feature_collection.type == "FeatureCollection"
        assert len(data_response.data.feature_collection.features) == 0
        assert len(data_response.data.succeed_transactions) == 0
        assert len(data_response.data.failed_transactions) == 0

    def test_location_file_download_error(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        from whimo.transactions.schemas.errors import LocationFileDownloadError

        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        mock_get_chain_feature_collection.side_effect = LocationFileDownloadError

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR, response_json
        assert response_json == snapshot

    def test_transaction_does_not_exist(
        self,
        client: APIClient,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        mock_get_chain_feature_collection.side_effect = NotFound()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        other_user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=other_user)

        mock_get_chain_feature_collection.side_effect = NotFound()

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_feature_collection_validation_error(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        mock_get_chain_feature_collection.side_effect = ValidationError.from_exception_data(
            "ValidationError",
            [
                {
                    "type": "value_error",
                    "loc": ("features", 0),
                    "input": None,
                    "ctx": {"error": "test error"},
                }
            ],
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

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

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_nonexistent_transaction_service_raises_not_found(self) -> None:
        # Arrange
        from whimo.transactions.services import TransactionsService

        nonexistent_id = UUID("00000000-0000-0000-0000-000000000000")

        # Act & Assert
        with pytest.raises(NotFound):
            TransactionsService.get_chain_feature_collection(nonexistent_id)

    def test_location_file_storage_exception_handling(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        mock_default_storage: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        from tests.factories.commodities import CommodityFactory
        from whimo.db.enums import TransactionLocation

        commodity = CommodityFactory.create()

        transaction = TransactionFactory.create(buyer=user, commodity=commodity, location=TransactionLocation.QR)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        mock_default_storage.open.side_effect = Exception("Storage error")

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR]

    def test_location_file_invalid_json_handling(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        mock_default_storage: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        from tests.factories.commodities import CommodityFactory
        from whimo.db.enums import TransactionLocation

        commodity = CommodityFactory.create()

        transaction = TransactionFactory.create(buyer=user, commodity=commodity, location=TransactionLocation.QR)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        mock_file = MagicMock()
        mock_file.read.return_value.decode.return_value = '{"invalid": json}'
        mock_default_storage.open.return_value = mock_file

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR]

    def test_location_file_invalid_geojson_handling(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        mock_default_storage: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        from tests.factories.commodities import CommodityFactory
        from whimo.db.enums import TransactionLocation

        commodity = CommodityFactory.create()

        transaction = TransactionFactory.create(buyer=user, commodity=commodity, location=TransactionLocation.QR)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        mock_file = MagicMock()
        mock_file.read.return_value.decode.return_value = '{"valid": "json", "but": "not_geojson"}'
        mock_default_storage.open.return_value = mock_file

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code in [HTTPStatus.OK, HTTPStatus.INTERNAL_SERVER_ERROR]

    def test_producer_create_without_recipient(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        from tests.factories.commodities import CommodityFactory

        commodity = CommodityFactory.create()

        url = reverse("transactions_producer_create")
        client.login(user)

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": "10.5",
            "location": "MANUAL",
        }

        # Act
        response = client.post(path=url, data=request_data, format="multipart")

        # Assert
        assert response.status_code in [HTTPStatus.CREATED, HTTPStatus.BAD_REQUEST]

    def test_throttling(
        self,
        client: APIClient,
        snapshot: SnapshotAssertion,
        mock_get_chain_feature_collection: MagicMock,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        mock_feature_collection = FeatureCollection(type="FeatureCollection", features=[])
        mock_succeed_transactions: list[UUID] = []
        mock_failed_transactions: list[UUID] = []

        mock_get_chain_feature_collection.return_value = (
            mock_feature_collection,
            mock_succeed_transactions,
            mock_failed_transactions,
        )

        # Act
        for _i in range(10):
            response = client.get(path=url)
            assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN]

        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot

    def test_location_file_error(
        self,
        client: APIClient,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        def mock_get_feature_collections(*_: Any, **__: Any) -> None:
            raise LocationFileDownloadError

        mocker.patch(
            "whimo.transactions.services.TransactionsService._get_feature_collections",
            side_effect=mock_get_feature_collections,
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_feature_collections_validation_error(
        self,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user, location=TransactionLocation.QR)

        mock_open = MagicMock()
        mock_open.read.return_value.decode.return_value = '{"invalid": "geojson"}'

        def mock_default_storage_open(_: str) -> MagicMock:
            return mock_open

        mocker.patch("whimo.transactions.services.default_storage.open", side_effect=mock_default_storage_open)
        mocker.patch("whimo.transactions.services.json.loads", return_value={"invalid": "geojson"})

        def mock_validate_raises(*_: Any, **__: Any) -> Never:
            error_details: InitErrorDetails = {
                "type": "missing",
                "loc": ("features",),
                "input": {},
                "ctx": {"field_name": "features"},
            }
            raise ValidationError.from_exception_data("test", [error_details])

        mocker.patch(
            "whimo.transactions.schemas.dto.FeatureCollection.model_validate", side_effect=mock_validate_raises
        )

        # Act
        transactions_qs = Transaction.objects.filter(id=transaction.id)
        feature_collections, succeed_transactions, failed_transactions = TransactionsService._get_feature_collections(
            transactions_qs
        )

        # Assert
        assert len(feature_collections) == 0
        assert len(succeed_transactions) == 0
        assert transaction.id in failed_transactions

    def test_get_feature_collections_non_qr_location(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.MANUAL)
        transactions = Transaction.objects.filter(id=transaction.id)

        # Act
        collections, succeed_transactions, failed_transactions = TransactionsService._get_feature_collections(
            transactions
        )

        # Assert
        assert len(collections) == 0
        assert len(succeed_transactions) == 0
        assert transaction.pk in failed_transactions

    def test_get_feature_collections_storage_exception(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        with patch("whimo.transactions.services.default_storage.open") as mock_open:
            mock_open.side_effect = Exception("Storage error")

            # Act & Assert
            with pytest.raises(LocationFileDownloadError):
                TransactionsService._get_feature_collections(transactions)

    def test_get_feature_collections_success_with_transaction_id(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        valid_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-122.4194, 37.7749, 0]]],
                    },
                    "properties": {
                        "ProducerName": "Test Producer",
                        "ProducerCountry": "Test Country",
                        "ProductionPlace": "Test Place",
                    },
                }
            ],
        }

        mock_file = Mock()
        mock_file.read.return_value.decode.return_value = json.dumps(valid_geojson)

        with patch("whimo.transactions.services.default_storage.open", return_value=mock_file):
            # Act
            collections, succeed_transactions, failed_transactions = TransactionsService._get_feature_collections(
                transactions
            )

            # Assert
            assert len(collections) == 1
            assert transaction.pk in succeed_transactions
            assert len(failed_transactions) == 0

            feature = collections[0].features[0]
            assert feature.properties.transaction_id == str(transaction.pk)

    def test_process_chain_location_bundle_non_qr_location(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.MANUAL)
        transactions = Transaction.objects.filter(id=transaction.id)

        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w")

        # Act
        result = TransactionsService._process_chain_location_bundle(transactions, zip_file)
        zip_file.close()

        geojson_merged, custom_location_file, no_location_file = result

        # Assert
        assert len(geojson_merged) == 0
        assert len(custom_location_file) == 0
        assert transaction.pk in no_location_file

    def test_process_chain_location_bundle_storage_error(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w")

        with patch("whimo.transactions.services.default_storage.open") as mock_open:
            mock_open.side_effect = Exception("Storage error")

            # Act
            result = TransactionsService._process_chain_location_bundle(transactions, zip_file)
            zip_file.close()

            geojson_merged, custom_location_file, no_location_file = result

            # Assert
            assert len(geojson_merged) == 0
            assert transaction.pk in custom_location_file
            assert transaction.pk in no_location_file

    def test_process_chain_location_bundle_json_decode_error(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w")

        mock_file = Mock()
        mock_file.read.return_value.decode.return_value = "invalid json"

        with patch("whimo.transactions.services.default_storage.open", return_value=mock_file):
            # Act
            result = TransactionsService._process_chain_location_bundle(transactions, zip_file)
            zip_file.close()

            geojson_merged, custom_location_file, no_location_file = result

            # Assert
            assert len(geojson_merged) == 0
            assert transaction.pk in custom_location_file
            assert transaction.pk in no_location_file

    def test_process_chain_location_bundle_validation_error(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w")

        invalid_geojson = {"invalid": "geojson structure"}
        mock_file = Mock()
        mock_file.read.return_value.decode.return_value = json.dumps(invalid_geojson)

        with patch("whimo.transactions.services.default_storage.open", return_value=mock_file):
            # Act
            result = TransactionsService._process_chain_location_bundle(transactions, zip_file)
            zip_file.close()

            geojson_merged, custom_location_file, no_location_file = result

            # Assert
            assert len(geojson_merged) == 0
            assert transaction.pk in custom_location_file
            assert transaction.pk in no_location_file

    def test_process_chain_location_bundle_success_path(self) -> None:
        # Arrange
        transaction = TransactionFactory.create(location=TransactionLocation.QR)
        transactions = Transaction.objects.filter(id=transaction.id)

        zip_buffer = BytesIO()
        zip_file = zipfile.ZipFile(zip_buffer, "w")

        valid_geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[-122.4194, 37.7749, 0]]],
                    },
                    "properties": {
                        "ProducerName": "Test Producer",
                        "ProducerCountry": "Test Country",
                        "ProductionPlace": "Test Place",
                    },
                }
            ],
        }

        mock_file = Mock()
        mock_file.read.return_value.decode.return_value = json.dumps(valid_geojson)

        with patch("whimo.transactions.services.default_storage.open", return_value=mock_file):
            # Act
            result = TransactionsService._process_chain_location_bundle(transactions, zip_file)
            zip_file.close()

            geojson_merged, custom_location_file, no_location_file = result

            # Assert
            assert transaction.pk in geojson_merged
            assert transaction.pk in custom_location_file
            assert len(no_location_file) == 0

            zip_buffer.seek(0)
            with zipfile.ZipFile(zip_buffer, "r") as read_zip:
                assert f"{transaction.id}.geojson" in read_zip.namelist()
                assert "merged.geojson" in read_zip.namelist()

    def test_get_or_create_recipient_no_request(self) -> None:
        # Act
        user, is_created = TransactionsService._get_or_create_recipient(None)

        # Assert
        assert user is None
        assert is_created is False
