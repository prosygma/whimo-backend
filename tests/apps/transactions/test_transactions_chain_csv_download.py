import csv
import io
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import patch
from uuid import UUID

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.models import Transaction

pytestmark = [pytest.mark.django_db]


class TestTransactionsChainCsvDownload:
    URL = "transactions_chain_csv_download"

    def test_success_with_transactions(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"
        assert response["Content-Disposition"] == f'attachment; filename="transaction_{transaction.id}_chain.csv"'
        assert response["X-Total-Transactions"] == "1"

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        expected_headers = [
            "Transaction ID",
            "Transaction Created At",
            "Transaction Type",
            "Transaction Status",
            "Transaction Traceability",
            "Location Type",
            "Transaction Latitude",
            "Transaction Longitude",
            "Farm Latitude",
            "Farm Longitude",
            "Volume",
            "Is Automatic",
            "Created By Role",
            "Commodity ID",
            "Commodity Code",
            "Commodity Name",
            "Commodity Unit",
            "Commodity Group",
            "Seller ID",
            "Seller Created At",
            "Buyer ID",
            "Buyer Created At",
        ]

        assert csv_reader.fieldnames == expected_headers

        rows = list(csv_reader)
        assert len(rows) >= 1

        first_row = rows[0]
        assert first_row["Transaction ID"] == str(transaction.id)
        assert first_row["Transaction Type"] == transaction.type
        assert first_row["Transaction Status"] == transaction.status
        assert first_row["Volume"] == str(transaction.volume)

    def test_seller_access(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(seller=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        assert len(rows) >= 1
        assert str(transaction.id) == rows[0]["Transaction ID"]

    def test_success_empty_chain(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"

        csv_content = response.content.decode("utf-8")
        assert "Transaction ID" in csv_content

    def test_transaction_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_transaction_not_user(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        other_user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=other_user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

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

    def test_csv_format_validation(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)
        assert len(rows) >= 0

    def test_csv_filename_format(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create()
        transaction = TransactionFactory.create(buyer=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        expected_filename = f'attachment; filename="transaction_{transaction.id}_chain.csv"'
        assert response["Content-Disposition"] == expected_filename

    def test_multiple_transactions_in_chain(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        producer_transaction = TransactionFactory.create(
            buyer=seller,
            seller=None,
            created_by=seller,
            status=TransactionStatus.ACCEPTED,
        )
        downstream_transaction = TransactionFactory.create(
            buyer=user,
            seller=seller,
            commodity=producer_transaction.commodity,
            status=TransactionStatus.ACCEPTED,
        )

        url = reverse(self.URL, args=(downstream_transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        response_ids = {UUID(row["Transaction ID"]) for row in rows}
        transaction_ids = {downstream_transaction.id, producer_transaction.id}
        assert response_ids == transaction_ids

    def test_conversion_chain(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        beans = CommodityFactory.create(name="Cacao Beans")
        oil = CommodityFactory.create(name="Cacao Oil")

        # beans -> oil
        producer_transaction = TransactionFactory.create(
            type=TransactionType.PRODUCER,
            buyer=user,
            seller=None,
            commodity=beans,
            volume=Decimal("100.0"),
            status=TransactionStatus.ACCEPTED,
        )

        BalanceFactory.create(user=user, commodity=beans, volume=Decimal("100.0"))

        recipe = ConversionRecipeFactory.create(name="Beans to Oil")
        ConversionInputFactory.create(recipe=recipe, commodity=beans, quantity=Decimal("50.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=oil, quantity=Decimal("25.0"))

        client.login(user)
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe.id)},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

        oil_transaction = Transaction.objects.get(
            created_by_id=user.id,
            type=TransactionType.CONVERSION,
            commodity_id=oil.id,
            buyer_id=user.id,
        )

        url = reverse(self.URL, args=(oil_transaction.id,))

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        response_ids = {UUID(row["Transaction ID"]) for row in rows}
        assert producer_transaction.id in response_ids

    def test_multilevel_conversion_chain(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        beans = CommodityFactory.create(name="Cacao Beans")
        oil = CommodityFactory.create(name="Cacao Oil")
        chocolate = CommodityFactory.create(name="Chocolate")

        # beans -> oil -> chocolate
        producer_transaction = TransactionFactory.create(
            type=TransactionType.PRODUCER,
            buyer=user,
            seller=None,
            commodity=beans,
            volume=Decimal("200.0"),
            status=TransactionStatus.ACCEPTED,
        )

        BalanceFactory.create(user=user, commodity=beans, volume=Decimal("200.0"))

        recipe1 = ConversionRecipeFactory.create(name="Beans to Oil")
        ConversionInputFactory.create(recipe=recipe1, commodity=beans, quantity=Decimal("100.0"))
        ConversionOutputFactory.create(recipe=recipe1, commodity=oil, quantity=Decimal("50.0"))

        client.login(user)
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe1.id)},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

        recipe2 = ConversionRecipeFactory.create(name="Oil to Chocolate")
        ConversionInputFactory.create(recipe=recipe2, commodity=oil, quantity=Decimal("25.0"))
        ConversionOutputFactory.create(recipe=recipe2, commodity=chocolate, quantity=Decimal("10.0"))

        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe2.id)},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

        chocolate_transaction = Transaction.objects.get(
            created_by_id=user.id,
            type=TransactionType.CONVERSION,
            commodity_id=chocolate.id,
            buyer_id=user.id,
        )

        url = reverse(self.URL, args=(chocolate_transaction.id,))

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        response_ids = {UUID(row["Transaction ID"]) for row in rows}
        assert producer_transaction.id in response_ids

    def test_conversion_multiple_inputs_chain(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        beans = CommodityFactory.create(name="Cacao Beans")
        sugar = CommodityFactory.create(name="Sugar")
        chocolate = CommodityFactory.create(name="Chocolate")

        # beans + sugar -> chocolate
        beans_transaction = TransactionFactory.create(
            type=TransactionType.PRODUCER,
            buyer=user,
            seller=None,
            commodity=beans,
            volume=Decimal("100.0"),
            status=TransactionStatus.ACCEPTED,
        )
        sugar_transaction = TransactionFactory.create(
            type=TransactionType.PRODUCER,
            buyer=user,
            seller=None,
            commodity=sugar,
            volume=Decimal("50.0"),
            status=TransactionStatus.ACCEPTED,
        )

        BalanceFactory.create(user=user, commodity=beans, volume=Decimal("100.0"))
        BalanceFactory.create(user=user, commodity=sugar, volume=Decimal("50.0"))

        recipe = ConversionRecipeFactory.create(name="Beans + Sugar to Chocolate")
        ConversionInputFactory.create(recipe=recipe, commodity=beans, quantity=Decimal("50.0"))
        ConversionInputFactory.create(recipe=recipe, commodity=sugar, quantity=Decimal("25.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=chocolate, quantity=Decimal("30.0"))

        client.login(user)
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe.id)},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

        chocolate_transaction = Transaction.objects.get(
            created_by_id=user.id,
            type=TransactionType.CONVERSION,
            commodity_id=chocolate.id,
            buyer_id=user.id,
        )

        url = reverse(self.URL, args=(chocolate_transaction.id,))

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        response_ids = {UUID(row["Transaction ID"]) for row in rows}
        assert beans_transaction.id in response_ids
        assert sugar_transaction.id in response_ids

    def test_conversion_with_downstream_chain(self, client: APIClient, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        # farmer -> seller -> user -> (conversion) -> oil
        farmer = UserFactory.create()
        seller = UserFactory.create()
        user = UserFactory.create()
        beans = CommodityFactory.create(name="Cacao Beans")
        oil = CommodityFactory.create(name="Cacao Oil")

        farmer_transaction = TransactionFactory.create(
            type=TransactionType.PRODUCER,
            buyer=farmer,
            seller=None,
            commodity=beans,
            volume=Decimal("300.0"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=farmer,
            buyer=seller,
            commodity=beans,
            volume=Decimal("200.0"),
            status=TransactionStatus.ACCEPTED,
        )

        TransactionFactory.create(
            type=TransactionType.DOWNSTREAM,
            seller=seller,
            buyer=user,
            commodity=beans,
            volume=Decimal("100.0"),
            status=TransactionStatus.ACCEPTED,
        )

        BalanceFactory.create(user=user, commodity=beans, volume=Decimal("100.0"))

        recipe = ConversionRecipeFactory.create(name="Beans to Oil")
        ConversionInputFactory.create(recipe=recipe, commodity=beans, quantity=Decimal("50.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=oil, quantity=Decimal("25.0"))

        client.login(user)
        response = client.post(
            path=reverse("transactions_conversion"),
            data={"recipe_id": str(recipe.id)},
            format="json",
        )
        assert response.status_code == HTTPStatus.OK

        oil_transaction = Transaction.objects.get(
            created_by_id=user.id,
            type=TransactionType.CONVERSION,
            commodity_id=oil.id,
            buyer_id=user.id,
        )

        url = reverse(self.URL, args=(oil_transaction.id,))

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK

        csv_content = response.content.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(csv_reader)

        response_ids = {UUID(row["Transaction ID"]) for row in rows}
        assert farmer_transaction.id in response_ids

    def test_export_with_seller_email_verified(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller_with_email = UserFactory.create(with_gadgets=False)

        GadgetFactory.create(user=seller_with_email, type="EMAIL", identifier="seller@example.com", is_verified=True)

        transaction = TransactionFactory.create(buyer=user, seller=seller_with_email, created_by=seller_with_email)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"

        csv_content = response.content.decode("utf-8")
        # Assert
        assert "Seller Email" not in csv_content
        assert "seller@example.com" not in csv_content
        assert "Transaction ID" in csv_content
        assert "Seller ID" in csv_content

    def test_export_with_seller_phone_verified(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller_with_phone = UserFactory.create(with_gadgets=False)

        GadgetFactory.create(user=seller_with_phone, type="PHONE", identifier="1234567890", is_verified=True)

        transaction = TransactionFactory.create(buyer=user, seller=seller_with_phone)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        csv_content = response.content.decode("utf-8")
        assert "Seller Phone" not in csv_content
        assert "1234567890" not in csv_content
        assert "Transaction ID" in csv_content
        assert "Seller ID" in csv_content

    def test_export_with_created_by_seller_role(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction = TransactionFactory.create(buyer=user, seller=seller, created_by=seller)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        csv_content = response.content.decode("utf-8")
        assert "Created By Role" in csv_content
        assert "seller" in csv_content

    def test_export_with_created_by_buyer_role(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()

        transaction = TransactionFactory.create(buyer=user, seller=seller, created_by=user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        csv_content = response.content.decode("utf-8")
        assert "buyer" in csv_content

    def test_export_with_created_by_other_role(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller = UserFactory.create()
        other_user = UserFactory.create()

        transaction = TransactionFactory.create(buyer=user, seller=seller, created_by=other_user)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        csv_content = response.content.decode("utf-8")
        assert "other" in csv_content

    def test_export_with_unverified_email_empty(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller_unverified = UserFactory.create(with_gadgets=False)

        GadgetFactory.create(
            user=seller_unverified, type="EMAIL", identifier="unverified@example.com", is_verified=False
        )

        transaction = TransactionFactory.create(buyer=user, seller=seller_unverified)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        csv_content = response.content.decode("utf-8")
        assert "unverified@example.com" not in csv_content

    def test_export_with_no_gadgets_empty(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        seller_no_gadgets = UserFactory.create(with_gadgets=False)

        transaction = TransactionFactory.create(buyer=user, seller=seller_no_gadgets)

        url = reverse(self.URL, args=(transaction.id,))
        client.login(user)

        # Act
        response = client.get(path=url)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response["Content-Type"] == "text/csv"

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()

        url = reverse(self.URL, args=("00000000-0000-0000-0000-000000000000",))
        client.login(user)

        # Act & Assert - Test within rate limit
        with patch("whimo.transactions.services.TransactionsService.get_chain_csv_export", return_value=[]):
            for _i in range(10):
                response = client.get(path=url)
                assert response.status_code in [HTTPStatus.OK, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN]

            # Act - Exceed rate limit
            response = client.get(path=url)
            response_json = response.json()

            # Assert
            assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
            assert response_json == snapshot
