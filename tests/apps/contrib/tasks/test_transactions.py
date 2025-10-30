from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture

from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.contrib.tasks.transactions import expire_transactions
from whimo.db.enums import TransactionStatus
from whimo.db.models import Notification, Transaction

pytestmark = [pytest.mark.django_db]


class TestTransactionsTasks:
    def test_expire_transactions_task(
        self,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()

        expired_time = timezone.now() - timedelta(hours=1)
        expired_transaction1 = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            expires_at=expired_time,
        )
        expired_transaction2 = TransactionFactory.create(
            seller=buyer,
            buyer=user,
            status=TransactionStatus.PENDING,
            expires_at=expired_time,
        )

        future_time = timezone.now() + timedelta(hours=1)
        active_transaction = TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            expires_at=future_time,
        )

        mock_send_push = mocker.patch(
            "whimo.notifications.services.notifications_push.NotificationsPushService.send_push"
        )

        # Act
        expire_transactions()

        # Assert
        expired_transaction1.refresh_from_db()
        expired_transaction2.refresh_from_db()
        active_transaction.refresh_from_db()

        assert expired_transaction1.status == TransactionStatus.NO_RESPONSE
        assert expired_transaction1.expires_at is None

        assert expired_transaction2.status == TransactionStatus.NO_RESPONSE
        assert expired_transaction2.expires_at is None

        assert active_transaction.status == TransactionStatus.PENDING
        assert active_transaction.expires_at == future_time

        notifications = Notification.objects.all()
        expected_notification_count = 2
        assert notifications.count() == expected_notification_count

        expected_push_call_count = 2
        assert mock_send_push.call_count == expected_push_call_count

    def test_expire_transactions_no_expired_transactions(
        self,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        buyer = UserFactory.create()

        future_time = timezone.now() + timedelta(hours=1)
        TransactionFactory.create(
            seller=user,
            buyer=buyer,
            status=TransactionStatus.PENDING,
            expires_at=future_time,
        )

        mock_send_push = mocker.patch(
            "whimo.notifications.services.notifications_push.NotificationsPushService.send_push"
        )

        # Act
        expire_transactions()

        # Assert
        transactions = Transaction.objects.all()
        for transaction in transactions:
            assert transaction.status == TransactionStatus.PENDING
            assert transaction.expires_at is not None

        assert Notification.objects.count() == 0

        mock_send_push.assert_not_called()
