from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.commodities import TransactionInline

pytestmark = [pytest.mark.django_db]


class TestCommoditiesAdmin:
    CHANGE_URL = "admin:db_commodity_change"
    CHANGELIST_URL = "admin:db_commodity_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create()

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
        CommodityFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_transaction_inline_display_methods(self) -> None:
        # Arrange
        transaction = TransactionFactory.create()

        # Act
        short_id_result = TransactionInline.short_id(None, transaction)
        seller_link_result = TransactionInline.seller_link(None, transaction)
        buyer_link_result = TransactionInline.buyer_link(None, transaction)

        # Assert
        assert short_id_result is not None
        assert seller_link_result is not None
        assert buyer_link_result is not None
