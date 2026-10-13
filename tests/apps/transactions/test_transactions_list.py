import math
from datetime import date, timedelta
from decimal import Decimal
from http import HTTPStatus

import factory
import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, MEDIUM_BATCH_SIZE, SMALL_BATCH_SIZE
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.db.enums import HarvestSeasonStatus, TransactionAction, TransactionStatus, TransactionType
from whimo.transactions.schemas.dto import TransactionDTO

pytestmark = [pytest.mark.django_db]


class TestTransactionsList:
    URL = reverse("transactions_list")

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buying = TransactionFactory.create_batch(size=2, buyer=user)
        selling = TransactionFactory.create_batch(size=2, seller=user)
        TransactionFactory.create_batch(size=2)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)

        response_ids = {transaction.id for transaction in data_response.data}
        request_ids = {transaction.id for transaction in buying + selling}
        assert response_ids == request_ids

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select count
        # 4. select entities
        # 5. select buyers gadgets
        # 6. select sellers gadgets
        assert len(queries) == 6, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_search_by_commodity_name(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
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

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].commodity.id == transaction.commodity.id

    def test_search_by_commodity_code(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        search_term = transaction.commodity.code[:3]
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?search={search_term}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].commodity.id == transaction.commodity.id

    @pytest.mark.parametrize("status", TransactionStatus)
    def test_filter_by_status(
        self,
        status: TransactionStatus,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        TransactionFactory.create_batch(
            size=len(TransactionStatus),
            status=factory.Iterator(TransactionStatus),
            buyer=user,
        )

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?status={status.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].status == status

    @pytest.mark.parametrize("action", TransactionAction)
    def test_filter_by_action(
        self,
        action: TransactionAction,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, seller=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?action={action.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE
        assert all(transaction.action == action for transaction in data_response.data)

    @pytest.mark.parametrize(
        ("transaction_type", "is_automatic", "side", "volume", "signed_volume"),
        [
            (TransactionType.DOWNSTREAM, False, "buyer", Decimal(500), Decimal(500)),
            (TransactionType.DOWNSTREAM, False, "seller", Decimal(500), Decimal(-500)),
            (TransactionType.PRODUCER, False, "buyer", Decimal(500), Decimal(500)),
            (TransactionType.PRODUCER, True, "buyer", Decimal(500), Decimal(500)),
            (TransactionType.CONVERSION, False, "seller", Decimal(-1000), Decimal(-1000)),
            (TransactionType.CONVERSION, False, "buyer", Decimal(850), Decimal(850)),
        ],
    )
    def test_signed_volume(  # noqa: PLR0913 Too many arguments in function definition
        self,
        transaction_type: TransactionType,
        is_automatic: bool,
        side: str,
        volume: Decimal,
        signed_volume: Decimal,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        transaction = TransactionFactory.create(
            type=transaction_type,
            is_automatic=is_automatic,
            volume=volume,
            **{side: user},
        )

        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].signed_volume == signed_volume
        assert data_response.data[0].volume == transaction.volume

    def test_filter_by_created_at_from(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        created_at_from = (DEFAULT_DATETIME + timedelta(days=15)).strftime("%Y-%m-%d")
        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?created_at_from={created_at_from}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

    def test_filter_by_created_at_to(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        created_at_to = (DEFAULT_DATETIME + timedelta(days=15)).strftime("%Y-%m-%d")
        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?created_at_to={created_at_to}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == SMALL_BATCH_SIZE

    def test_filter_by_commodity_group(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_group_id={transaction.commodity.group.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == transaction.id

    def test_filter_by_commodity_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?commodity_id={transaction.commodity.id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == transaction.id
        assert data_response.data[0].commodity.id == transaction.commodity.id

    def test_filter_by_harvest_season_id(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE, buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?harvest_season_id={transaction.harvest_season_id}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == transaction.id
        assert data_response.data[0].harvest_season.id == transaction.harvest_season_id

    def test_filter_by_harvest_season_status(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
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
        response = client.get(path=f"{self.URL}?harvest_season_status={HarvestSeasonStatus.PAST.value}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == past.id

    def test_filter_by_buyer(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(buyer=buyer, status=TransactionStatus.ACCEPTED)
        TransactionFactory.create_batch(size=SMALL_BATCH_SIZE)

        client.login(user)
        filters = (
            f"buyer_id={buyer.id}"
            f"&commodity_group_id={transaction.commodity.group.id}"
            f"&status={TransactionStatus.ACCEPTED}"
        )

        # Act
        response = client.get(path=f"{self.URL}?{filters}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == transaction.id

    def test_filter_by_buyer_without_commodity_group(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()

        client.login(user)
        filters = f"buyer_id={buyer.id}&status={TransactionStatus.ACCEPTED}"

        # Act
        response = client.get(path=f"{self.URL}?{filters}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_filter_by_buyer_without_status_accepted(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(buyer=buyer, status=TransactionStatus.ACCEPTED)

        client.login(user)
        filters = f"buyer_id={buyer.id}&commodity_group_id={transaction.commodity.group.id}"

        # Act
        response = client.get(path=f"{self.URL}?{filters}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

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
        TransactionFactory.create_batch(size=MEDIUM_BATCH_SIZE, buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?page={page}&page_size={page_size}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)

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
        TransactionFactory.create(buyer=user, commodity__name="Banana")
        TransactionFactory.create(buyer=user, commodity__name="Apple")
        TransactionFactory.create(buyer=user, commodity__name="Cherry")

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=commodity_name")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
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
        TransactionFactory.create(buyer=user, commodity__name="Banana")
        TransactionFactory.create(buyer=user, commodity__name="Apple")
        TransactionFactory.create(buyer=user, commodity__name="Cherry")

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=-commodity_name")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
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
        TransactionFactory.create(buyer=user, volume=50)
        TransactionFactory.create(buyer=user, volume=10)
        TransactionFactory.create(buyer=user, volume=30)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=amount")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
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
        TransactionFactory.create(buyer=user, volume=50)
        TransactionFactory.create(buyer=user, volume=10)
        TransactionFactory.create(buyer=user, volume=30)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=-amount")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].volume == 50  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[1].volume == 30  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[2].volume == 10  # noqa: PLR2004 Magic value used in comparison

    def test_order_by_created_at_asc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=2))
        TransactionFactory.create(buyer=user)

        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create(buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=1))
        TransactionFactory.create(buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=created_at")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].created_at < data_response.data[1].created_at  # type: ignore
        assert data_response.data[1].created_at < data_response.data[2].created_at  # type: ignore

    def test_order_by_created_at_desc(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create(buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=1))
        TransactionFactory.create(buyer=user)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=2))
        TransactionFactory.create(buyer=user)

        client.login(user)

        # Act
        response = client.get(path=f"{self.URL}?orderings=-created_at")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 3  # noqa: PLR2004 Magic value used in comparison
        assert data_response.data[0].created_at > data_response.data[1].created_at  # type: ignore
        assert data_response.data[1].created_at > data_response.data[2].created_at  # type: ignore

    def test_combined_filters(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        freezer.move_to(DEFAULT_DATETIME)
        transaction = TransactionFactory.create(buyer=user, status=TransactionStatus.PENDING)

        freezer.move_to(DEFAULT_DATETIME + timedelta(days=30))
        TransactionFactory.create(buyer=user, status=TransactionStatus.ACCEPTED)

        freezer.move_to(DEFAULT_DATETIME)
        TransactionFactory.create(seller=user, status=TransactionStatus.PENDING)

        client.login(user)
        mid_month = DEFAULT_DATETIME + timedelta(days=15)
        filters = (
            f"action={TransactionAction.BUYING.value}"
            f"&status={TransactionStatus.PENDING.value}"
            f"&created_at_to={mid_month.strftime('%Y-%m-%d')}"
        )

        # Act
        response = client.get(path=f"{self.URL}?{filters}")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
        assert len(data_response.data) == 1
        assert data_response.data[0].id == transaction.id
        assert data_response.data[0].status == TransactionStatus.PENDING
        assert data_response.data[0].action == TransactionAction.BUYING

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

        data_response = PaginatedDataResponse[list[TransactionDTO]](**response_json)
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
