from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.balances import BalanceFactory
from tests.factories.notifications import NotificationFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.users import (
    BalanceInline,
    BuyingInline,
    NotificationReceivedInline,
    SellingInline,
)

pytestmark = [pytest.mark.django_db]


class TestUsersAdmin:
    CHANGE_URL = "admin:db_user_change"
    CHANGELIST_URL = "admin:db_user_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = UserFactory.create()

        url = reverse(self.CHANGE_URL, args=(entity.pk,))

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(entity.pk) in response_content

    def test_changelist(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        UserFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_balance_inline_commodity_link(self) -> None:
        # Arrange
        balance = BalanceFactory.create()

        # Act
        result = BalanceInline.commodity_link(None, balance)

        # Assert
        assert result is not None

    def test_selling_inline_display_methods(self) -> None:
        # Arrange
        transaction = TransactionFactory.create()

        # Act
        short_id_result = SellingInline.short_id(None, transaction)
        commodity_link_result = SellingInline.commodity_link(None, transaction)
        buyer_link_result = SellingInline.buyer_link(None, transaction)

        # Assert
        assert short_id_result is not None
        assert commodity_link_result is not None
        assert buyer_link_result is not None

    def test_buying_inline_display_methods(self) -> None:
        # Arrange
        transaction = TransactionFactory.create()

        # Act
        short_id_result = BuyingInline.short_id(None, transaction)
        commodity_link_result = BuyingInline.commodity_link(None, transaction)
        seller_link_result = BuyingInline.seller_link(None, transaction)

        # Assert
        assert short_id_result is not None
        assert commodity_link_result is not None
        assert seller_link_result is not None

    def test_notification_received_inline_display_methods(self) -> None:
        # Arrange
        notification = NotificationFactory.create()

        # Act
        short_id_result = NotificationReceivedInline.short_id(None, notification)
        created_by_link_result = NotificationReceivedInline.created_by_link(None, notification)

        # Assert
        assert short_id_result is not None
        assert created_by_link_result is not None
