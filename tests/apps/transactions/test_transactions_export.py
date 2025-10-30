import pytest

from tests.factories.transactions import TransactionFactory
from tests.factories.users import GadgetFactory, UserFactory
from whimo.db.models import Transaction
from whimo.transactions.export.resources import TransactionAdminResource, TransactionUserResource

pytestmark = [pytest.mark.django_db]


class TestTransactionExportResources:
    def test_transaction_admin_resource_dehydrate_methods(self) -> None:
        # Arrange
        seller_with_contacts = UserFactory.create(with_gadgets=False)
        buyer_with_contacts = UserFactory.create(with_gadgets=False)
        other_user = UserFactory.create()

        GadgetFactory.create(user=seller_with_contacts, type="EMAIL", identifier="seller@example.com", is_verified=True)
        GadgetFactory.create(user=seller_with_contacts, type="PHONE", identifier="+1234567890", is_verified=True)
        GadgetFactory.create(user=buyer_with_contacts, type="EMAIL", identifier="buyer@example.com", is_verified=True)
        GadgetFactory.create(user=buyer_with_contacts, type="PHONE", identifier="+0987654321", is_verified=True)

        transaction_seller_created = TransactionFactory.create(
            buyer=buyer_with_contacts, seller=seller_with_contacts, created_by=seller_with_contacts
        )
        transaction_buyer_created = TransactionFactory.create(
            buyer=buyer_with_contacts, seller=seller_with_contacts, created_by=buyer_with_contacts
        )
        transaction_other_created = TransactionFactory.create(
            buyer=buyer_with_contacts, seller=seller_with_contacts, created_by=other_user
        )

        transaction_seller_created = (
            Transaction.objects.select_related("seller", "buyer")
            .prefetch_related("seller__gadgets", "buyer__gadgets")
            .get(pk=transaction_seller_created.pk)
        )

        resource = TransactionAdminResource()

        # Act & Assert
        assert resource.dehydrate_seller_email(transaction_seller_created) == "seller@example.com"
        assert resource.dehydrate_seller_phone(transaction_seller_created) == "+1234567890"
        assert resource.dehydrate_buyer_email(transaction_seller_created) == "buyer@example.com"
        assert resource.dehydrate_buyer_phone(transaction_seller_created) == "+0987654321"

        assert resource.dehydrate_created_by_role(transaction_seller_created) == "seller"
        assert resource.dehydrate_created_by_role(transaction_buyer_created) == "buyer"
        assert resource.dehydrate_created_by_role(transaction_other_created) == "other"

    def test_transaction_admin_resource_empty_gadgets(self) -> None:
        # Arrange
        seller_no_gadgets = UserFactory.create(with_gadgets=False)
        buyer_no_gadgets = UserFactory.create(with_gadgets=False)

        transaction = TransactionFactory.create(buyer=buyer_no_gadgets, seller=seller_no_gadgets)

        resource = TransactionAdminResource()

        # Act & Assert
        assert resource.dehydrate_seller_email(transaction) == ""
        assert resource.dehydrate_seller_phone(transaction) == ""
        assert resource.dehydrate_buyer_email(transaction) == ""
        assert resource.dehydrate_buyer_phone(transaction) == ""

    def test_transaction_admin_resource_unverified_gadgets(self) -> None:
        # Arrange
        seller_unverified = UserFactory.create(with_gadgets=False)
        buyer_unverified = UserFactory.create(with_gadgets=False)

        GadgetFactory.create(
            user=seller_unverified, type="EMAIL", identifier="unverified@example.com", is_verified=False
        )
        GadgetFactory.create(user=buyer_unverified, type="PHONE", identifier="+9999999999", is_verified=False)

        transaction = TransactionFactory.create(buyer=buyer_unverified, seller=seller_unverified)

        resource = TransactionAdminResource()

        # Act & Assert
        assert resource.dehydrate_seller_email(transaction) == ""
        assert resource.dehydrate_buyer_phone(transaction) == ""

    def test_transaction_admin_resource_null_users(self) -> None:
        # Arrange
        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=None, seller=None, created_by=user)
        resource = TransactionAdminResource()

        # Act & Assert
        assert resource.dehydrate_seller_email(transaction) == ""
        assert resource.dehydrate_seller_phone(transaction) == ""
        assert resource.dehydrate_buyer_email(transaction) == ""
        assert resource.dehydrate_buyer_phone(transaction) == ""

    def test_transaction_user_resource_dehydrate_created_by_role(self) -> None:
        # Arrange
        seller = UserFactory.create()
        buyer = UserFactory.create()
        other_user = UserFactory.create()

        transaction_seller_created = TransactionFactory.create(buyer=buyer, seller=seller, created_by=seller)
        transaction_buyer_created = TransactionFactory.create(buyer=buyer, seller=seller, created_by=buyer)
        transaction_other_created = TransactionFactory.create(buyer=buyer, seller=seller, created_by=other_user)

        resource = TransactionUserResource()

        # Act & Assert
        assert resource.dehydrate_created_by_role(transaction_seller_created) == "seller"
        assert resource.dehydrate_created_by_role(transaction_buyer_created) == "buyer"
        assert resource.dehydrate_created_by_role(transaction_other_created) == "other"
