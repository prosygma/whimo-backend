from decimal import Decimal
from http import HTTPStatus

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Balance, Transaction

pytestmark = [pytest.mark.django_db]


class TestRecipeBasedConversion:
    URL = reverse("transactions_conversion")

    def test_success_with_recipe_defaults(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {"recipe_id": str(recipe.id)}

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        expected_transaction_count = 2
        assert len(transactions) == expected_transaction_count

        input_transaction = transactions[0]
        assert input_transaction.commodity_id == input_commodity.id
        assert input_transaction.volume == Decimal("-10.0")
        assert input_transaction.seller_id == user.id
        assert input_transaction.buyer_id is None

        output_transaction = transactions[1]
        assert output_transaction.commodity_id == output_commodity.id
        assert output_transaction.volume == Decimal("5.0")
        assert output_transaction.seller_id is None
        assert output_transaction.buyer_id == user.id

        input_balance = Balance.objects.get(user=user, commodity=input_commodity)
        assert input_balance.volume == Decimal("10.0")

        output_balance = Balance.objects.get(user=user, commodity=output_commodity)
        assert output_balance.volume == Decimal("5.0")

    def test_success_with_input_overrides(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("50.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "input_overrides": [{"commodity_id": str(input_commodity.id), "quantity": "25.0"}],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        input_transaction = transactions[0]
        assert input_transaction.volume == Decimal("-25.0")

        input_balance = Balance.objects.get(user=user, commodity=input_commodity)
        assert input_balance.volume == Decimal("25.0")

    def test_success_with_output_overrides(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "output_overrides": [{"commodity_id": str(output_commodity.id), "quantity": "8.0"}],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        output_transaction = transactions[1]
        assert output_transaction.volume == Decimal("8.0")

        output_balance = Balance.objects.get(user=user, commodity=output_commodity)
        assert output_balance.volume == Decimal("8.0")

    def test_success_with_zero_quantity_override(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity_1 = CommodityFactory.create()
        input_commodity_2 = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity_1, quantity=Decimal("10.0"))
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity_2, quantity=Decimal("5.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("8.0"))

        BalanceFactory.create(user=user, commodity=input_commodity_1, volume=Decimal("20.0"))
        BalanceFactory.create(user=user, commodity=input_commodity_2, volume=Decimal("20.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "input_overrides": [{"commodity_id": str(input_commodity_2.id), "quantity": "0"}],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        expected_transaction_count = 2
        assert len(transactions) == expected_transaction_count

        input_transaction = transactions[0]
        assert input_transaction.commodity_id == input_commodity_1.id
        assert input_transaction.volume == Decimal("-10.0")

        balance_2 = Balance.objects.get(user=user, commodity=input_commodity_2)
        assert balance_2.volume == Decimal("20.0")

    def test_recipe_not_found(
        self,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        client.login(user)

        request_data = {"recipe_id": "00000000-0000-0000-0000-000000000000"}

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_invalid_override_commodity(
        self,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()
        invalid_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "input_overrides": [{"commodity_id": str(invalid_commodity.id), "quantity": "5.0"}],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_insufficient_balance(
        self,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("100.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("50.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("50.0"))

        request_data = {"recipe_id": str(recipe.id)}

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_all_inputs_zero_error(
        self,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "input_overrides": [{"commodity_id": str(input_commodity.id), "quantity": "0"}],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_duplicate_input_override(
        self,
        client: APIClient,
    ) -> None:
        # Arrange
        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        request_data = {
            "recipe_id": str(recipe.id),
            "input_overrides": [
                {"commodity_id": str(input_commodity.id), "quantity": "5.0"},
                {"commodity_id": str(input_commodity.id), "quantity": "10.0"},
            ],
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_traceability_inheritance(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        from tests.factories.transactions import TransactionFactory

        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        TransactionFactory.create(
            buyer=user,
            commodity=input_commodity,
            volume=Decimal("20.0"),
            traceability=TransactionTraceability.FULL,
            status=TransactionStatus.ACCEPTED,
        )

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        request_data = {"recipe_id": str(recipe.id)}

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        for transaction in transactions:
            assert transaction.traceability == TransactionTraceability.FULL

    def test_group_id_is_set_for_conversion_transactions(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("10.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("5.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {"recipe_id": str(recipe.id)}
        client.login(user)

        response = client.post(path=self.URL, data=request_data, format="json")

        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        assert len(transactions) == 2  # noqa PLR2004 Magic value used in comparison

        input_transaction = transactions[0]
        output_transaction = transactions[1]

        assert input_transaction.group_id is not None
        assert output_transaction.group_id is not None
        assert input_transaction.group_id == output_transaction.group_id

    def test_group_id_is_unique_per_conversion(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity = CommodityFactory.create()
        output_commodity = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Test Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity, quantity=Decimal("5.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity, quantity=Decimal("2.0"))

        BalanceFactory.create(user=user, commodity=input_commodity, volume=Decimal("20.0"))

        request_data = {"recipe_id": str(recipe.id)}
        client.login(user)

        response1 = client.post(path=self.URL, data=request_data, format="json")
        assert response1.status_code == HTTPStatus.OK

        response2 = client.post(path=self.URL, data=request_data, format="json")
        assert response2.status_code == HTTPStatus.OK

        all_transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("created_at")
        )

        assert len(all_transactions) == 4  # noqa PLR2004 Magic value used in comparison

        group_ids = [t.group_id for t in all_transactions]

        assert len(set(group_ids)) == 2  # noqa PLR2004 Magic value used in comparison

        first_group_id = all_transactions[0].group_id
        second_group_id = all_transactions[2].group_id

        assert first_group_id != second_group_id

        first_group_transactions = [t for t in all_transactions if t.group_id == first_group_id]
        second_group_transactions = [t for t in all_transactions if t.group_id == second_group_id]

        assert len(first_group_transactions) == 2  # noqa PLR2004 Magic value used in comparison
        assert len(second_group_transactions) == 2  # noqa PLR2004 Magic value used in comparison

    def test_group_id_with_multiple_inputs_and_outputs(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        input_commodity_1 = CommodityFactory.create()
        input_commodity_2 = CommodityFactory.create()
        output_commodity_1 = CommodityFactory.create()
        output_commodity_2 = CommodityFactory.create()

        recipe = ConversionRecipeFactory.create(name="Multi Recipe")
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity_1, quantity=Decimal("10.0"))
        ConversionInputFactory.create(recipe=recipe, commodity=input_commodity_2, quantity=Decimal("5.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity_1, quantity=Decimal("8.0"))
        ConversionOutputFactory.create(recipe=recipe, commodity=output_commodity_2, quantity=Decimal("3.0"))

        BalanceFactory.create(user=user, commodity=input_commodity_1, volume=Decimal("20.0"))
        BalanceFactory.create(user=user, commodity=input_commodity_2, volume=Decimal("10.0"))

        request_data = {"recipe_id": str(recipe.id)}
        client.login(user)

        response = client.post(path=self.URL, data=request_data, format="json")

        assert response.status_code == HTTPStatus.OK

        transactions = list(
            Transaction.objects.filter(created_by_id=user.id, type=TransactionType.CONVERSION).order_by("volume")
        )

        assert len(transactions) == 4  # noqa PLR2004 Magic value used in comparison

        group_ids = [t.group_id for t in transactions]

        for group_id in group_ids:
            assert group_id is not None

        assert all(g == group_ids[0] for g in group_ids)
