from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.balances import BalanceFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient

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
