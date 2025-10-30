from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import factory
import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.balances import BalanceFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Notification, Transaction

pytestmark = [pytest.mark.django_db]


class TestTransactionsAccept:
    URL = "transactions_status_update"

    def test_traceability_full(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction_volume = 100

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            created_by=seller,
            volume=transaction_volume,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
            expires_at=DEFAULT_DATETIME + timedelta(days=1),
        )

        TransactionFactory.create(
            buyer=seller,
            producer=True,
            traceability=TransactionTraceability.FULL,
            commodity=transaction.commodity,
        )
        BalanceFactory.create(user=seller, commodity=transaction.commodity, volume=transaction_volume)

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.ACCEPTED
        assert transaction.traceability == TransactionTraceability.FULL
        assert transaction.expires_at is None

        notification = Notification.objects.get()

        assert notification.type == NotificationType.TRANSACTION_ACCEPTED
        assert notification.status == NotificationStatus.PENDING
        assert notification.data["transaction"]["id"] == str(transaction.pk)  # type: ignore
        assert notification.received_by_id == seller.id
        assert notification.created_by_id == user.id

    @pytest.mark.parametrize(
        "traceability_list",
        [
            (
                TransactionTraceability.FULL,
                TransactionTraceability.CONDITIONAL,
                TransactionTraceability.PARTIAL,
                TransactionTraceability.INCOMPLETE,
            ),
            (
                TransactionTraceability.FULL,
                TransactionTraceability.CONDITIONAL,
                TransactionTraceability.PARTIAL,
            ),
            (
                TransactionTraceability.FULL,
                TransactionTraceability.CONDITIONAL,
            ),
            (TransactionTraceability.FULL,),
        ],
    )
    def test_worst_previous_traceability(
        self,
        client: APIClient,
        traceability_list: list[TransactionTraceability],
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction_volume = 100

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            created_by=seller,
            volume=transaction_volume,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        TransactionFactory.create_batch(
            size=len(traceability_list),
            buyer=seller,
            producer=True,
            commodity=transaction.commodity,
            traceability=factory.Iterator(traceability_list),
        )
        BalanceFactory.create(user=seller, commodity=transaction.commodity, volume=transaction_volume)

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.ACCEPTED
        assert transaction.traceability == traceability_list[-1]

    def test_no_previous_transactions(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction_volume = 100

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            created_by=seller,
            volume=transaction_volume,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        BalanceFactory.create(user=seller, commodity=transaction.commodity, volume=transaction_volume)

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.ACCEPTED
        assert transaction.traceability == TransactionTraceability.INCOMPLETE

    def test_negative_volume(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction_volume = 100
        seller_volume = transaction_volume // 3

        transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            created_by=seller,
            volume=transaction_volume,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        TransactionFactory.create(buyer=seller, producer=True, traceability=TransactionTraceability.FULL)
        seller_balance = BalanceFactory.create(user=seller, commodity=transaction.commodity, volume=seller_volume)

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transaction.refresh_from_db()
        assert transaction.status == TransactionStatus.ACCEPTED
        assert transaction.traceability == TransactionTraceability.INCOMPLETE

        automatic_transaction = Transaction.objects.get(volume=Decimal(transaction_volume - seller_volume))

        assert automatic_transaction.type == TransactionType.PRODUCER
        assert automatic_transaction.status == TransactionStatus.ACCEPTED
        assert automatic_transaction.traceability == TransactionTraceability.INCOMPLETE

        assert automatic_transaction.location is None
        assert automatic_transaction.transaction_latitude is None
        assert automatic_transaction.transaction_longitude is None

        assert automatic_transaction.commodity == transaction.commodity
        assert automatic_transaction.volume == transaction_volume - seller_volume

        assert not automatic_transaction.is_buying_from_farmer
        assert automatic_transaction.is_automatic

        assert automatic_transaction.seller is None
        assert automatic_transaction.buyer == seller
        assert automatic_transaction.created_by == seller

        seller_balance.refresh_from_db()
        assert seller_balance.volume == 0

    def test_transaction_expired(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()

        transaction = TransactionFactory.create(
            buyer=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
            expires_at=DEFAULT_DATETIME - timedelta(days=1),
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_does_not_exist(
        self,
        client: APIClient,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_pending(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.REJECTED,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_created_by_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            created_by=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": TransactionStatus.ACCEPTED,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    @pytest.mark.parametrize("status", [TransactionStatus.PENDING, TransactionStatus.NO_RESPONSE])
    def test_invalid_status(
        self,
        status: TransactionStatus,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(
            buyer=user,
            type=TransactionType.DOWNSTREAM,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(transaction.id,))
        request_data = {
            "status": status,
        }

        client.login(user)

        # Act
        response = client.patch(path=url, data=request_data)
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
