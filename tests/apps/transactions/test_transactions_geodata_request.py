from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.commodities import CommodityFactory
from tests.factories.notifications import NotificationFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification
from whimo.transactions.services import TransactionsService

pytestmark = [pytest.mark.django_db]


class TestTransactionsGeodataRequest:
    URL = "transactions_geodata_request"

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    def test_creates_notifications_for_missing_geodata(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        # -(  no  )> seller3_1 -(  no  )> seller2_1  |
        # -(  no  )> seller3_2 -(  no  )> seller2_1  |  seller2_1 -(passed)> seller1_1 | seller1_1 -(passed)> user
        #            seller3_2 -(  no  )> seller2_2  |  seller2_2 -(passed)> seller1_1 |
        # -(passed)> seller3_3 -(  no  )> seller2_2  |
        # ---
        # notified: seller3_1, seller3_2

        seller3_1 = UserFactory.create()
        seller3_2 = UserFactory.create()
        seller3_3 = UserFactory.create()

        seller2_1 = UserFactory.create()
        seller2_2 = UserFactory.create()

        seller1_1 = UserFactory.create()

        TransactionFactory.create(
            producer=True,
            buyer=seller3_1,
            location=None,
            commodity=commodity,
        )

        TransactionFactory.create(
            producer=True,
            buyer=seller3_2,
            location=None,
            commodity=commodity,
        )

        TransactionFactory.create(
            producer=True,
            buyer=seller3_3,
            commodity=commodity,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_1,
            buyer=seller2_1,
            location=None,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_2,
            buyer=seller2_1,
            location=None,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_2,
            buyer=seller2_2,
            location=None,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller3_3,
            buyer=seller2_2,
            location=None,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller2_1,
            buyer=seller1_1,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller2_2,
            buyer=seller1_1,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        user_transaction = TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller1_1,
            buyer=user,
            commodity=commodity,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(user_transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        notifications = Notification.objects.filter(type=NotificationType.GEODATA_MISSING)

        assert notifications.count() == 2  # noqa: PLR2004

        assert notifications.filter(received_by=seller3_1).count() == 1
        assert notifications.filter(received_by=seller3_2).count() == 1

    def test_no_notifications_when_no_missing_geodata(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        chain_seller = UserFactory.create()
        chain_buyer = UserFactory.create()

        TransactionFactory.create(
            commodity=commodity,
            seller=chain_seller,
            buyer=chain_buyer,
            status=TransactionStatus.ACCEPTED,
        )

        user_transaction = TransactionFactory.create(
            commodity=commodity,
            buyer=user,
            seller=chain_buyer,
        )

        url = reverse(self.URL, args=(user_transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        notifications = Notification.objects.filter(
            type=NotificationType.GEODATA_MISSING,
            created_by=user,
        )

        assert notifications.count() == 0

    def test_transaction_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        client.login(user)

        # Act
        response = client.post(path=url)
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
        transaction = TransactionFactory.create()

        url = reverse(self.URL, args=(transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))

        # Act
        response = client.post(path=url)
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
        response = client.post(path=url)
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
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_skips_notifications_when_buyer_absent(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        # Create a transaction chain where some transactions have no buyer_id
        seller1 = UserFactory.create()
        seller2 = UserFactory.create()

        # Transaction with no buyer_id (should be skipped)
        TransactionFactory.create(
            producer=True,
            buyer=None,
            location=None,
            commodity=commodity,
            created_by=seller1,
        )

        # Transaction with buyer_id (should create notification)
        TransactionFactory.create(
            producer=True,
            buyer=seller1,
            location=None,
            commodity=commodity,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller1,
            buyer=seller2,
            location=None,
            commodity=commodity,
            status=TransactionStatus.ACCEPTED,
        )

        user_transaction = TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller2,
            buyer=user,
            commodity=commodity,
            status=TransactionStatus.PENDING,
        )

        url = reverse(self.URL, args=(user_transaction.id,))

        client.login(user)

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        # Only one notification should be created (for seller1, not for the transaction with no buyer)
        notifications = Notification.objects.filter(type=NotificationType.GEODATA_MISSING)
        assert notifications.count() == 1
        assert notifications.filter(received_by=seller1).count() == 1

    def test_duplicate_geodata_missing_notification(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()
        transaction = TransactionFactory.create(seller=user, buyer=buyer)

        existing_notification = NotificationFactory.create(
            type=NotificationType.GEODATA_MISSING,
            status=NotificationStatus.PENDING,
            received_by=buyer,
            data={"transaction": {"id": str(transaction.id)}},
        )

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.post(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        geodata_missing_notifications = Notification.objects.filter(
            type=NotificationType.GEODATA_MISSING, data__transaction__id=str(transaction.id)
        )
        assert geodata_missing_notifications.count() == 1
        first_notification = geodata_missing_notifications.first()
        assert first_notification is not None
        assert first_notification.id == existing_notification.id

    def test_missing_buyer(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction_without_buyer = TransactionFactory.create(
            seller=user, buyer=None, status=TransactionStatus.PENDING, type=TransactionType.PRODUCER, created_by=user
        )

        url = reverse(self.URL, args=(transaction_without_buyer.id,))
        client.login(user)

        # Act
        response = client.post(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

    def test_request_missing_geodata_no_buyer_id(self) -> None:
        # Arrange
        user = UserFactory.create()
        buyer_user = UserFactory.create()
        commodity = CommodityFactory.create()

        TransactionFactory.create(
            producer=True,
            buyer=None,
            commodity=commodity,
            location=None,
            created_by=user,
        )

        TransactionFactory.create(
            producer=True,
            buyer=buyer_user,
            commodity=commodity,
            location=None,
            created_by=user,
        )

        main_transaction = TransactionFactory.create(
            seller=buyer_user,
            buyer=user,
            commodity=commodity,
            created_by=user,
        )

        with (
            patch(
                "whimo.notifications.services.notifications.NotificationsService.create_from_transaction"
            ) as mock_create,
            patch("whimo.notifications.services.notifications_push.NotificationsPushService.send_push"),
        ):
            # Act
            TransactionsService.request_missing_geodata(user.id, main_transaction.id)

            # Assert
            assert mock_create.call_count == 1
            call_args = mock_create.call_args[1]
            assert call_args["received_by_id"] == buyer_user.id
