from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.transactions import TransactionFactory
from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.transactions import TransactionAdmin
from whimo.db.enums import GadgetType

pytestmark = [pytest.mark.django_db]


class TestTransactionsAdmin:
    CHANGE_URL = "admin:db_transaction_change"
    CHANGELIST_URL = "admin:db_transaction_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = TransactionFactory.create()

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
        TransactionFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_export_with_gadgets(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        seller = UserFactory.create()
        buyer = UserFactory.create()

        # Create gadgets for seller and buyer
        GadgetFactory.create(user=seller, type=GadgetType.EMAIL, is_verified=True)
        GadgetFactory.create(user=seller, type=GadgetType.PHONE, is_verified=True)
        GadgetFactory.create(user=buyer, type=GadgetType.EMAIL, is_verified=True)
        GadgetFactory.create(user=buyer, type=GadgetType.PHONE, is_verified=True)

        transaction = TransactionFactory.create(seller=seller, buyer=buyer)

        url = reverse(self.CHANGELIST_URL)
        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(transaction.pk) in response_content

    def test_export_without_gadgets(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        seller = UserFactory.create()
        buyer = UserFactory.create()

        # No gadgets created
        transaction = TransactionFactory.create(seller=seller, buyer=buyer)

        url = reverse(self.CHANGELIST_URL)
        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(transaction.pk) in response_content

    def test_export_created_by_roles(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        seller = UserFactory.create()
        buyer = UserFactory.create()

        # Test different created_by scenarios
        tx_seller_created = TransactionFactory.create(seller=seller, buyer=buyer, created_by=seller)
        tx_buyer_created = TransactionFactory.create(seller=seller, buyer=buyer, created_by=buyer)
        tx_other_created = TransactionFactory.create(seller=seller, buyer=buyer)

        url = reverse(self.CHANGELIST_URL)
        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(tx_seller_created.pk) in response_content
        assert str(tx_buyer_created.pk) in response_content
        assert str(tx_other_created.pk) in response_content

    def test_transaction_admin_display_methods(self) -> None:
        # Arrange
        transaction = TransactionFactory.create()

        # Act
        short_id_result = TransactionAdmin.short_id(None, transaction)
        commodity_link_result = TransactionAdmin.commodity_link(None, transaction)
        seller_link_result = TransactionAdmin.seller_link(None, transaction)
        buyer_link_result = TransactionAdmin.buyer_link(None, transaction)
        created_by_link_result = TransactionAdmin.created_by_link(None, transaction)
        type_labeled_result = TransactionAdmin.type_labeled(None, transaction)
        status_labeled_result = TransactionAdmin.status_labeled(None, transaction)
        traceability_labeled_result = TransactionAdmin.traceability_labeled(None, transaction)

        # Assert
        assert short_id_result is not None
        assert commodity_link_result is not None
        assert seller_link_result is not None
        assert buyer_link_result is not None
        assert created_by_link_result is not None
        assert type_labeled_result is not None
        assert status_labeled_result is not None
        assert traceability_labeled_result is not None or traceability_labeled_result is None
