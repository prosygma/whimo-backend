import csv
import io
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import patch

import factory
import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, SMALL_BATCH_SIZE
from whimo.db.enums import TransactionAction, TransactionStatus

pytestmark = [pytest.mark.django_db]


class TestTransactionsListCsvDownload:
    URL = reverse("transactions_list_csv_download")

    def test_success_with_transactions(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buying = TransactionFactory.create_batch(size=2, buyer=user)
        selling = TransactionFactory.create_batch(size=2, seller=user)
        TransactionFactory.create_batch(size=2)

        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"] == 'attachment; filename="transactions.csv"'
        assert response["X-Total-Transactions"] == "4"

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        expected_headers = [
            "Transaction ID",
            "Transaction Created At",
            "Transaction Type",
            "Transaction Status",
            "Transaction Traceability",
            "Location Type",
            "Transaction Latitude",
            "Transaction Longitude",
            "Farm Latitude",
            "Farm Longitude",
            "Volume",
            "Is Automatic",
            "Created By Role",
            "Commodity ID",
            "Commodity Code",
            "Commodity Name",
            "Commodity Unit",
            "Commodity Group",
            "Seller ID",
            "Seller Created At",
            "Buyer ID",
            "Buyer Created At",
        ]

        assert csv_reader.fieldnames == expected_headers

        rows = list(csv_reader)
        assert len(rows) == 4  # noqa: PLR2004 Magic value used in comparison

        response_ids = {row["Transaction ID"] for row in rows}
        request_ids = {str(t.id) for t in buying + selling}
        assert response_ids == request_ids

    def test_filter_by_status(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        TransactionFactory.create_batch(
            size=len(TransactionStatus),
            status=factory.Iterator(TransactionStatus),
            buyer=user,
        )

        client.login(user)

        response = client.get(path=f"{self.URL}?status={TransactionStatus.PENDING.value}")

        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == 1
        assert rows[0]["Transaction Status"] == TransactionStatus.PENDING.value

    def test_filter_by_action(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buying = TransactionFactory.create_batch(size=2, buyer=user)
        TransactionFactory.create_batch(size=2, seller=user)

        client.login(user)

        response = client.get(path=f"{self.URL}?action={TransactionAction.BUYING.value}")

        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == 2  # noqa: PLR2004 Magic value used in comparison
        response_ids = {row["Transaction ID"] for row in rows}
        request_ids = {str(t.id) for t in buying}
        assert response_ids == request_ids

    def test_filter_by_commodity_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        response = client.get(path=f"{self.URL}?commodity_id={transaction.commodity.id}")

        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == 1
        assert rows[0]["Transaction ID"] == str(transaction.id)
        assert rows[0]["Commodity ID"] == str(transaction.commodity.id)

    def test_filter_by_created_at_range(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create_batch(size=2, buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        new_transactions = TransactionFactory.create_batch(size=2, buyer=user)

        created_at_from = (DEFAULT_DATETIME + timedelta(days=15)).strftime("%Y-%m-%d")
        client.login(user)

        response = client.get(path=f"{self.URL}?created_at_from={created_at_from}")

        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == 2  # noqa: PLR2004 Magic value used in comparison
        response_ids = {row["Transaction ID"] for row in rows}
        new_ids = {str(t.id) for t in new_transactions}
        assert response_ids == new_ids

    def test_search_by_commodity_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        search_term = transaction.commodity.name[:3]
        TransactionFactory.create_batch(
            size=SMALL_BATCH_SIZE,
            buyer=user,
            commodity__name=factory.Faker("numerify", text="####"),
        )

        client.login(user)

        response = client.get(path=f"{self.URL}?search={search_term}")

        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) == 1
        assert rows[0]["Transaction ID"] == str(transaction.id)

    def test_empty_result(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"
        assert response["X-Total-Transactions"] == "0"

        csv_content = response.content.decode("utf-8")
        assert "Transaction ID" in csv_content

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

    def test_csv_filename_format(self, client: APIClient) -> None:
        user = UserFactory.create()
        TransactionFactory.create(buyer=user)

        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK

        expected_filename = 'attachment; filename="transactions.csv"'
        assert response["Content-Disposition"] == expected_filename

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        user = UserFactory.create()

        client.login(user)

        with patch("whimo.transactions.services.TransactionsService.get_list_csv_export", return_value=[]):
            for _i in range(10):
                response = client.get(path=self.URL)
                assert response.status_code in [HTTPStatus.OK, HTTPStatus.FORBIDDEN]

            response = client.get(path=self.URL)
            response_json = response.json()

            assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
            assert response_json == snapshot
