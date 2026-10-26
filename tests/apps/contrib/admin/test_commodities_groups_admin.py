from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient

pytestmark = [pytest.mark.django_db]


class TestCommoditiesGroupsAdmin:
    CHANGE_URL = "admin:db_commoditygroup_change"
    CHANGELIST_URL = "admin:db_commoditygroup_changelist"
    ARCHIVE_URL = "admin:db_commoditygroup_archive"
    RESTORE_URL = "admin:db_commoditygroup_restore"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityGroupFactory.create()

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
        CommodityGroupFactory.create_batch(size=5)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Asserts
        assert response.status_code == HTTPStatus.OK, response_content

    def test_changelist_hides_archived(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        group = CommodityGroupFactory.create()
        CommodityGroupFactory.create(is_archived=True)

        admin_client.login(admin)

        # Act
        response = admin_client.get(reverse(self.CHANGELIST_URL))

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert list(response.context["cl"].result_list) == [group]

    def test_archive_confirmation(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        group = CommodityGroupFactory.create()
        CommodityFactory.create_batch(size=2, group=group)

        admin_client.login(admin)

        # Act
        response = admin_client.get(reverse(self.ARCHIVE_URL, args=(group.pk,)))

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert response.context["commodities_count"] == 2  # noqa: PLR2004 Magic value used in comparison

    def test_archive_archives_commodities(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        group = CommodityGroupFactory.create()
        commodities = CommodityFactory.create_batch(size=2, group=group)
        other_commodity = CommodityFactory.create()

        admin_client.login(admin)

        # Act
        response = admin_client.post(reverse(self.ARCHIVE_URL, args=(group.pk,)))

        # Assert
        assert response.status_code == HTTPStatus.FOUND
        group.refresh_from_db()
        assert group.is_archived
        for commodity in commodities:
            commodity.refresh_from_db()
            assert commodity.is_archived
            assert commodity.history.first().is_archived  # type: ignore[attr-defined]
        other_commodity.refresh_from_db()
        assert not other_commodity.is_archived

    def test_restore_restores_commodities(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        group = CommodityGroupFactory.create(is_archived=True)
        commodities = CommodityFactory.create_batch(size=2, group=group, is_archived=True)

        admin_client.login(admin)

        # Act
        response = admin_client.post(reverse(self.RESTORE_URL, args=(group.pk,)))

        # Assert
        assert response.status_code == HTTPStatus.FOUND
        group.refresh_from_db()
        assert not group.is_archived
        for commodity in commodities:
            commodity.refresh_from_db()
            assert not commodity.is_archived
