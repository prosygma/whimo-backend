import pytest
from freezegun.api import FrozenDateTimeFactory

from tests.factories.notifications import NotificationFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.notifications.services.notifications import NotificationsService

pytestmark = [pytest.mark.django_db]


class TestNotificationsService:
    def test_create_from_transaction_duplicate_geodata_missing(
        self,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        transaction = TransactionFactory.create()
        existing_notification = NotificationFactory.create(
            type=NotificationType.GEODATA_MISSING,
            status=NotificationStatus.PENDING,
            received_by=user,
            data={"transaction": {"id": str(transaction.id)}},
        )

        # Act
        result_notification = NotificationsService.create_from_transaction(
            notification_type=NotificationType.GEODATA_MISSING,
            transaction=transaction,
            received_by_id=user.id,
        )

        # Assert
        assert result_notification.id == existing_notification.id
        assert result_notification.type == NotificationType.GEODATA_MISSING
