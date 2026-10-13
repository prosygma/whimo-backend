import json
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from pytest_mock import MockerFixture

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_EMAIL
from whimo.commodities.schemas.dto import CommodityGroupWithCommoditiesBalancesDTO
from whimo.common.schemas.base import PaginatedDataResponse
from whimo.common.test_mode import enable_test_mode
from whimo.db.enums import GadgetType, TransactionAction, TransactionLocation, TransactionStatus, TransactionType
from whimo.db.models import Balance, Gadget, Notification, Transaction
from whimo.transactions.schemas.dto import TransactionDTO

pytestmark = [pytest.mark.django_db(transaction=True, databases=["default", "test_mode"])]

TEST_MODE_PRODUCER_URL = "/api/v1/test/transactions/producer/"
TEST_MODE_DOWNSTREAM_URL = "/api/v1/test/transactions/downstream/"
TEST_MODE_LIST_URL = "/api/v1/test/transactions/"
TEST_MODE_CONVERSION_URL = "/api/v1/test/transactions/conversion/"
TEST_MODE_BALANCES_URL = "/api/v1/test/commodities/balances/"
TEST_MODE_GROUPS_URL = "/api/v1/test/commodities/groups/"
TEST_MODE_USER_ANALYTICS_URL = "/api/v1/test/analytics/user/"


class TestTestModeIsolation:
    def test_a_producer_transaction_created_under_test_is_invisible_to_the_normal_list(
        self,
        client: APIClient,
    ) -> None:
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        client.login(user)

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": TransactionLocation.MANUAL,
            "transaction_latitude": 0,
            "transaction_longitude": 0,
            "farm_latitude": 1,
            "farm_longitude": 1,
            "is_buying_from_farmer": True,
        }

        response = client.post(path=TEST_MODE_PRODUCER_URL, data=request_data, format="multipart")
        response_json = response.json()
        assert response.status_code == HTTPStatus.OK, response_json

        normal_response = client.get(path=reverse("transactions_list"))
        normal_data = PaginatedDataResponse[list[TransactionDTO]](**normal_response.json())
        assert normal_data.data == []

        test_response = client.get(path=TEST_MODE_LIST_URL)
        test_data = PaginatedDataResponse[list[TransactionDTO]](**test_response.json())
        assert len(test_data.data) == 1
        assert test_data.data[0].commodity.id == commodity.id

        transaction_id = response_json["data"]["id"]
        assert Transaction.objects.using("test_mode").filter(pk=transaction_id, type=TransactionType.PRODUCER).exists()
        assert not Transaction.objects.using("default").filter(pk=transaction_id).exists()

    def test_real_balances_are_invisible_under_test(self, client: APIClient) -> None:
        user = UserFactory.create()
        BalanceFactory.create(user=user)
        client.login(user)

        normal_response = client.get(path=reverse("commodities_balances_list"))
        test_response = client.get(path=TEST_MODE_BALANCES_URL)

        assert len(normal_response.json()["data"]) == 1
        assert test_response.json()["data"] == []

    def test_a_recipient_invited_under_test_is_registered_without_an_invite(
        self,
        client: APIClient,
        mock_create_username: MagicMock,
        mock_invite_email: MagicMock,
    ) -> None:
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        mock_create_username.return_value = "John Doe"
        client.login(user)

        response = client.post(
            path=TEST_MODE_DOWNSTREAM_URL,
            data={
                "commodity_id": str(commodity.id),
                "harvest_season_id": str(commodity.harvest_seasons.get().id),
                "volume": 1,
                "action": TransactionAction.SELLING,
                "recipient": json.dumps({"email": USER_EMAIL}),
            },
            format="json",
        )

        assert response.status_code == HTTPStatus.OK, response.json()
        recipient_id = Gadget.objects.get(type=GadgetType.EMAIL, identifier=USER_EMAIL).user_id
        transaction = Transaction.objects.using("test_mode").get(pk=response.json()["data"]["id"])
        assert transaction.buyer_id == recipient_id
        assert Notification.objects.using("test_mode").filter(received_by_id=recipient_id).exists()
        assert not Transaction.objects.using("default").exists()
        mock_invite_email.assert_not_called()

    def test_accepting_under_test_moves_test_balances_only(self, client: APIClient) -> None:
        buyer = UserFactory.create()
        seller = UserFactory.create()
        commodity = CommodityFactory.create()
        BalanceFactory.create(user=seller, commodity=commodity, volume=Decimal("100.00"))
        with enable_test_mode():
            BalanceFactory.create(user=seller, commodity=commodity, volume=Decimal("100.00"))
            transaction = TransactionFactory.create(
                buyer=buyer,
                seller=seller,
                created_by=seller,
                commodity=commodity,
                volume=Decimal("40.00"),
                type=TransactionType.DOWNSTREAM,
                status=TransactionStatus.PENDING,
            )
        client.login(buyer)

        response = client.patch(
            path=f"/api/v1/test/transactions/{transaction.id}/status/",
            data={"status": TransactionStatus.ACCEPTED},
        )

        assert response.status_code == HTTPStatus.OK, response.json()
        test_balances = Balance.objects.using("test_mode").filter(commodity=commodity)
        assert {balance.user_id: balance.volume for balance in test_balances} == {
            seller.id: Decimal("60.00"),
            buyer.id: Decimal("40.00"),
        }
        assert Balance.objects.using("default").get(user=seller).volume == Decimal("100.00")
        assert not Balance.objects.using("default").filter(user=buyer).exists()
        assert Notification.objects.using("test_mode").filter(received_by=seller).exists()
        assert not Notification.objects.using("default").exists()

    def test_a_conversion_under_test_leaves_real_balances_untouched(self, client: APIClient) -> None:
        user = UserFactory.create()
        cocoa = CommodityFactory.create()
        butter = CommodityFactory.create(group=cocoa.group)
        recipe = ConversionRecipeFactory.create()
        ConversionInputFactory.create(recipe=recipe, commodity=cocoa, quantity=Decimal("10.00"))
        ConversionOutputFactory.create(recipe=recipe, commodity=butter, quantity=Decimal("4.00"))
        season = cocoa.harvest_seasons.get()
        BalanceFactory.create(user=user, commodity=cocoa, volume=Decimal("50.00"))
        with enable_test_mode():
            BalanceFactory.create(user=user, commodity=cocoa, volume=Decimal("50.00"))
        client.login(user)

        response = client.post(
            path=TEST_MODE_CONVERSION_URL,
            data={"recipe_id": str(recipe.id), "harvest_season_id": str(season.id)},
            format="json",
        )

        assert response.status_code == HTTPStatus.OK, response.json()
        test_balances = Balance.objects.using("test_mode").filter(user=user)
        assert {balance.commodity_id: balance.volume for balance in test_balances} == {
            cocoa.id: Decimal("40.00"),
            butter.id: Decimal("4.00"),
        }
        assert Balance.objects.using("default").get(user=user).volume == Decimal("50.00")
        assert not Transaction.objects.using("default").exists()

    def test_commodity_groups_under_test_show_test_balances(self, client: APIClient) -> None:
        user = UserFactory.create()
        commodity = CommodityFactory.create()
        BalanceFactory.create(user=user, commodity=commodity, volume=Decimal("100.00"))
        with enable_test_mode():
            BalanceFactory.create(user=user, commodity=commodity, volume=Decimal("7.00"))
        client.login(user)

        response = client.get(path=TEST_MODE_GROUPS_URL)

        assert response.status_code == HTTPStatus.OK, response.json()
        data = PaginatedDataResponse[list[CommodityGroupWithCommoditiesBalancesDTO]](**response.json()).data
        assert data[0].commodities[0].balance == Decimal("7.00")

    def test_user_analytics_under_test_count_test_transactions(self, client: APIClient, mocker: MockerFixture) -> None:
        mocker.patch("whimo.analytics.services.default_storage.exists", return_value=False)
        user = UserFactory.create()
        TransactionFactory.create(producer=True, buyer=user)
        client.login(user)

        normal_response = client.get(path=reverse("user_analytics"))
        test_response = client.get(path=TEST_MODE_USER_ANALYTICS_URL)

        assert normal_response.json()["data"]["total_transactions"] == 1
        assert test_response.json()["data"]["total_transactions"] == 0
