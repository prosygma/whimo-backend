from http import HTTPStatus

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from tests.factories.commodities import CommodityFactory
from tests.factories.conversions import ConversionInputFactory, ConversionOutputFactory, ConversionRecipeFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.contrib.admin.commodities import TransactionInline
from whimo.db.models import ConversionInput

pytestmark = [pytest.mark.django_db]


class TestCommoditiesAdmin:
    CHANGE_URL = "admin:db_commodity_change"
    CHANGELIST_URL = "admin:db_commodity_changelist"
    ARCHIVE_URL = "admin:db_commodity_archive"
    RESTORE_URL = "admin:db_commodity_restore"
    AUTOCOMPLETE_URL = "admin:autocomplete"

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

    @pytest.mark.parametrize(
        ("query", "expected_codes"),
        [("", ["ACTIVE"]), ("?status=archived", ["ARCHIVED"]), ("?status=all", ["ACTIVE", "ARCHIVED"])],
    )
    def test_changelist_status_filter(self, query: str, expected_codes: list[str], admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        CommodityFactory.create(code="ACTIVE")
        CommodityFactory.create(code="ARCHIVED", is_archived=True)

        admin_client.login(admin)

        # Act
        response = admin_client.get(reverse(self.CHANGELIST_URL) + query)

        # Assert
        assert response.status_code == HTTPStatus.OK
        assert sorted(item.code for item in response.context["cl"].result_list) == expected_codes

    def test_change_shows_archive_action(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create()

        admin_client.login(admin)

        # Act
        response = admin_client.get(reverse(self.CHANGE_URL, args=(entity.pk,)))
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert reverse(self.ARCHIVE_URL, args=(entity.pk,)) in response_content
        assert reverse(self.RESTORE_URL, args=(entity.pk,)) not in response_content

    def test_archive_confirmation(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create()
        TransactionFactory.create_batch(size=2, commodity=entity)
        ConversionInputFactory.create(commodity=entity)
        ConversionOutputFactory.create(commodity=entity)
        recipe = ConversionRecipeFactory.create()
        ConversionInputFactory.create(recipe=recipe, commodity=entity)
        ConversionOutputFactory.create(recipe=recipe)

        admin_client.login(admin)

        # Act
        response = admin_client.get(reverse(self.ARCHIVE_URL, args=(entity.pk,)))
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert response.context["commodities_count"] == 1
        assert response.context["transactions_count"] == 2  # noqa: PLR2004 Magic value used in comparison
        assert response.context["recipes_count"] == 3  # noqa: PLR2004 Magic value used in comparison
        entity.refresh_from_db()
        assert not entity.is_archived

    def test_archive(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create()

        admin_client.login(admin)

        # Act
        response = admin_client.post(reverse(self.ARCHIVE_URL, args=(entity.pk,)))

        # Assert
        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse(self.CHANGE_URL, args=(entity.pk,))
        entity.refresh_from_db()
        assert entity.is_archived
        assert entity.history.first().is_archived  # type: ignore[attr-defined]

    def test_restore(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create(is_archived=True)

        admin_client.login(admin)

        # Act
        response = admin_client.post(reverse(self.RESTORE_URL, args=(entity.pk,)))

        # Assert
        assert response.status_code == HTTPStatus.FOUND
        entity.refresh_from_db()
        assert not entity.is_archived

    def test_restore_with_archived_group(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        entity = CommodityFactory.create(is_archived=True, group__is_archived=True)

        admin_client.login(admin)

        # Act
        change_response = admin_client.get(reverse(self.CHANGE_URL, args=(entity.pk,)))
        restore_response = admin_client.post(reverse(self.RESTORE_URL, args=(entity.pk,)))

        # Assert
        assert reverse(self.RESTORE_URL, args=(entity.pk,)) not in change_response.content.decode()
        assert restore_response.status_code == HTTPStatus.FORBIDDEN
        entity.refresh_from_db()
        assert entity.is_archived

    @pytest.mark.parametrize(
        ("model_name", "expected_codes"),
        [("conversioninput", ["ACTIVE"]), ("conversionoutput", ["ACTIVE"]), ("transaction", ["ACTIVE", "ARCHIVED"])],
    )
    def test_autocomplete(self, model_name: str, expected_codes: list[str], admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        active = CommodityFactory.create(code="ACTIVE")
        archived = CommodityFactory.create(code="ARCHIVED", is_archived=True)
        codes = {str(active.pk): active.code, str(archived.pk): archived.code}

        admin_client.login(admin)

        # Act
        response = admin_client.get(
            reverse(self.AUTOCOMPLETE_URL),
            {"app_label": "db", "model_name": model_name, "field_name": "commodity", "term": ""},
        )
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert sorted(codes[item["id"]] for item in response_json["results"]) == expected_codes

    def test_conversion_rejects_archived_commodity(self) -> None:
        # Arrange
        recipe = ConversionRecipeFactory.create()
        commodity = CommodityFactory.create(is_archived=True)

        # Act & Assert
        with pytest.raises(ValidationError, match="archived commodity"):
            ConversionInput(recipe=recipe, commodity=commodity, quantity=1).full_clean()

    def test_conversion_keeps_existing_archived_commodity(self) -> None:
        # Arrange
        conversion_input = ConversionInputFactory.create()
        conversion_input.commodity.set_archived(True)
        conversion_input.quantity = 2

        # Act & Assert
        conversion_input.full_clean()

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
