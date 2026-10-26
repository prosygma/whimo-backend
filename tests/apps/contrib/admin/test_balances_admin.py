from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.balances import BalanceFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.balances import BalanceAdmin
from whimo.db.enums.harvest_seasons import HarvestSeasonStatus

pytestmark = [pytest.mark.django_db]


class TestBalancesAdmin:
    CHANGE_URL = "admin:db_balance_change"
    CHANGELIST_URL = "admin:db_balance_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = BalanceFactory.create()

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
        BalanceFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_balance_admin_display_methods(self) -> None:
        # Arrange
        balance = BalanceFactory.create()

        # Act
        short_id_result = BalanceAdmin.short_id(None, balance)
        user_link_result = BalanceAdmin.user_link(None, balance)
        commodity_link_result = BalanceAdmin.commodity_link(None, balance)
        harvest_season_link_result = BalanceAdmin.harvest_season_link(None, balance)
        harvest_season_status_result = BalanceAdmin.harvest_season_status_labeled(None, balance)

        # Assert
        assert short_id_result is not None
        assert user_link_result is not None
        assert commodity_link_result is not None
        assert harvest_season_link_result is not None
        assert harvest_season_status_result == HarvestSeasonStatus(balance.harvest_season.status).name
