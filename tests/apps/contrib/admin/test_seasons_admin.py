from datetime import timedelta
from http import HTTPStatus

import pytest
from django.urls import reverse
from django.utils import timezone

from tests.factories.seasons import SeasonFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.seasons import SeasonAdmin, SeasonTransactionInline

pytestmark = [pytest.mark.django_db]


class TestSeasonsAdmin:
    CHANGE_URL = "admin:db_season_change"
    CHANGELIST_URL = "admin:db_season_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = SeasonFactory.create()

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
        SeasonFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_season_transaction_inline_methods(self) -> None:
        # Arrange
        transaction = TransactionFactory.create()

        # Act
        short_id_result = SeasonTransactionInline.short_id(None, transaction)
        commodity_link_result = SeasonTransactionInline.commodity_link(None, transaction)
        seller_link_result = SeasonTransactionInline.seller_link(None, transaction)
        buyer_link_result = SeasonTransactionInline.buyer_link(None, transaction)

        # Assert
        assert short_id_result is not None
        assert commodity_link_result is not None
        assert seller_link_result is not None
        assert buyer_link_result is not None

    def test_season_admin_display_methods(self) -> None:
        # Arrange
        season = SeasonFactory.create()

        # Act
        short_id_result = SeasonAdmin.short_id(None, season)

        # Assert
        assert short_id_result is not None

    def test_status_labeled_method_all_branches(self) -> None:
        # Arrange
        today = timezone.now().date()
        upcoming_season = SeasonFactory.create(
            start_date=today + timedelta(days=1),
            end_date=today + timedelta(days=30),
        )
        completed_season = SeasonFactory.create(
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
        )
        active_season = SeasonFactory.create(start_date=today - timedelta(days=5), end_date=today + timedelta(days=5))

        # Act
        upcoming_result = SeasonAdmin.status_labeled(None, upcoming_season)
        completed_result = SeasonAdmin.status_labeled(None, completed_season)
        active_result = SeasonAdmin.status_labeled(None, active_season)

        # Assert
        assert upcoming_result == "Upcoming"
        assert completed_result == "Completed"
        assert active_result == "Active"
