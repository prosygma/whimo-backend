import csv
import io
from datetime import date, timedelta
from http import HTTPStatus
from unittest.mock import patch

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.apps.transactions.test_transactions_chain_bundle_download import farm, trade
from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.db.enums import HarvestSeasonStatus, TransactionAction, TransactionLocation, TransactionStatus

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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")

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
            "Harvest Season ID",
            "Harvest Season Name",
            "Harvest Season Start Date",
            "Harvest Season End Date",
            "Harvest Season Status",
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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
        rows = list(csv_reader)

        assert len(rows) == 1
        assert rows[0]["Transaction ID"] == str(transaction.id)
        assert rows[0]["Commodity ID"] == str(transaction.commodity.id)

    def test_archived_commodity_exported(self, client: APIClient) -> None:
        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user, commodity__is_archived=True)

        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        rows = list(csv.DictReader(io.StringIO(csv_content), delimiter=";"))

        assert [row["Transaction ID"] for row in rows] == [str(transaction.id)]
        assert rows[0]["Commodity ID"] == str(transaction.commodity.id)

    def test_every_row_carries_its_season(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transactions = TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK

        rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8")), delimiter=";"))
        assert len(rows) == SMALL_BATCH_SIZE

        seasons = {str(transaction.harvest_season_id): transaction.harvest_season for transaction in transactions}
        for row in rows:
            season = seasons[row["Harvest Season ID"]]
            assert row["Harvest Season Name"] == season.name
            assert row["Harvest Season Start Date"] == str(season.start_date)
            assert row["Harvest Season End Date"] == str(season.end_date)
            assert row["Harvest Season Status"] == season.status

    def test_filter_by_harvest_season(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create(with_harvest_season=False)
        past_season = HarvestSeasonFactory.create(
            start_date=date(2024, 9, 1),
            end_date=date(2025, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )
        active_season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        HarvestSeasonCommodityFactory.create(harvest_season=past_season, commodity=commodity)
        HarvestSeasonCommodityFactory.create(harvest_season=active_season, commodity=commodity)

        past = TransactionFactory.create(buyer=user, commodity=commodity, harvest_season=past_season)
        TransactionFactory.create(buyer=user, commodity=commodity, harvest_season=active_season)

        client.login(user)

        # Act
        by_id = client.get(path=f"{self.URL}?harvest_season_id={past_season.id}")
        by_status = client.get(path=f"{self.URL}?harvest_season_status={HarvestSeasonStatus.PAST.value}")

        # Assert
        assert by_id.status_code == HTTPStatus.OK
        assert by_status.status_code == HTTPStatus.OK
        assert by_id["X-Total-Transactions"] == "1"

        for response in (by_id, by_status):
            rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8")), delimiter=";"))
            assert len(rows) == 1
            assert rows[0]["Transaction ID"] == str(past.id)
            assert rows[0]["Harvest Season ID"] == str(past_season.id)

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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
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
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
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

    def test_include_chain_adds_the_upstream_suppliers(self, client: APIClient) -> None:
        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        harvest = farm(farmer, commodity, TransactionLocation.GPS, farm_latitude=1, farm_longitude=2)
        supply = trade(farmer, trader, commodity)
        purchase = trade(trader, user, commodity)

        client.login(user)

        response = client.get(path=f"{self.URL}?include_chain=true")

        assert response.status_code == HTTPStatus.OK
        assert response["X-Total-Transactions"] == "3"

        csv_reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")), delimiter=";")
        tiers = {row["Transaction ID"]: row["Tier"] for row in csv_reader}
        assert tiers == {str(purchase.id): "0", str(supply.id): "1", str(harvest.id): "2"}

    def test_include_chain_lists_a_shared_supplier_once(self, client: APIClient) -> None:
        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        supply = trade(farmer, trader, commodity)
        trade(trader, user, commodity)
        trade(trader, user, commodity)

        client.login(user)

        response = client.get(path=f"{self.URL}?include_chain=true")

        assert response.status_code == HTTPStatus.OK

        csv_reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")), delimiter=";")
        rows = [row["Transaction ID"] for row in csv_reader]
        assert rows.count(str(supply.id)) == 1
        assert len(rows) == 3  # noqa: PLR2004 Magic value used in comparison

    def test_without_include_chain_the_file_stops_at_the_user_rows(self, client: APIClient) -> None:
        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        trade(farmer, trader, commodity)
        purchase = trade(trader, user, commodity)

        client.login(user)

        response = client.get(path=self.URL)

        assert response.status_code == HTTPStatus.OK
        assert response["X-Total-Transactions"] == "1"

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content), delimiter=";")
        assert [row["Transaction ID"] for row in csv_reader] == [str(purchase.id)]
        assert "Tier" not in csv_content.splitlines()[0]

    def test_include_chain_query_count_follows_chain_depth(self, client: APIClient) -> None:
        user, trader, farmer = UserFactory.create(), UserFactory.create(), UserFactory.create()
        commodity = CommodityFactory.create()

        trade(farmer, trader, commodity)
        trade(trader, user, commodity)

        client.login(user)

        with CaptureQueriesContext(connection) as single_queries:
            client.get(path=f"{self.URL}?include_chain=true")

        for _ in range(MEDIUM_BATCH_SIZE):
            trade(trader, user, commodity)

        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=f"{self.URL}?include_chain=true")

        assert response.status_code == HTTPStatus.OK
        assert len(queries) == len(single_queries), queries_to_str(queries)

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
