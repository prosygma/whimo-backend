from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.notifications import NotificationFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.notifications import NotificationAdmin
from whimo.db.enums.notifications import NotificationType

pytestmark = [pytest.mark.django_db]


class TestNotificationsAdmin:
    CHANGE_URL = "admin:db_notification_change"
    CHANGELIST_URL = "admin:db_notification_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        admin_client.login(admin)
        entity = NotificationFactory.create()

        url = reverse(self.CHANGE_URL, args=(entity.pk,))

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(entity.pk) in response_content

    def test_changelist(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        admin_client.login(admin)
        NotificationFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_type_labeled_method_specific_types(self) -> None:
        # Arrange
        notification_accepted = NotificationFactory.create(type=NotificationType.TRANSACTION_ACCEPTED)
        notification_rejected = NotificationFactory.create(type=NotificationType.TRANSACTION_REJECTED)

        # Act
        result_accepted = NotificationAdmin.type_labeled(None, notification_accepted)
        result_rejected = NotificationAdmin.type_labeled(None, notification_rejected)

        # Assert
        assert "refresh" in str(result_accepted)
        assert "close" in str(result_rejected)
