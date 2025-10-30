import io
import zipfile
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME

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
        assert response.status_code == HTTPStatus.OK

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
