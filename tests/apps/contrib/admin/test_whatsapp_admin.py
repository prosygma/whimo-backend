from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.urls import reverse
from pytest_mock import MockerFixture

from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.db.models import WhatsAppSettings

pytestmark = [pytest.mark.django_db]


class TestWhatsAppSettingsAdmin:
    CHANGE_URL = "admin:db_whatsappsettings_change"
    CHANGELIST_URL = "admin:db_whatsappsettings_changelist"

    @pytest.fixture(autouse=True)
    def login(self, admin_client: AdminClient) -> None:
        admin_client.login(UserFactory.create(superuser=True))

    def form_data(self, **overrides: object) -> dict[str, object]:
        data = {
            "is_enabled": "on",
            "api_version": "v21.0",
            "phone_number_id": "123456789",
            "access_token": "",
            "template_name": "verification_code",
            "template_languages": '{"en-us": "en_US"}',
            "test_phone_number": "237690000000",
        }
        data.update(overrides)
        return {key: value for key, value in data.items() if value is not None}

    def test_changelist_opens_the_single_row(self, admin_client: AdminClient) -> None:
        response = admin_client.get(reverse(self.CHANGELIST_URL))

        config = WhatsAppSettings.objects.get()
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(self.CHANGE_URL, args=(config.pk,))

    def test_token_is_never_displayed(self, admin_client: AdminClient) -> None:
        config = WhatsAppSettings.load()
        config.access_token = "super-secret-token"
        config.save()

        response = admin_client.get(reverse(self.CHANGE_URL, args=(config.pk,)))

        assert response.status_code == HTTPStatus.OK
        assert "super-secret-token" not in response.content.decode()

    def test_blank_token_keeps_the_saved_one(self, admin_client: AdminClient) -> None:
        config = WhatsAppSettings.load()
        config.access_token = "saved-token"
        config.save()

        response = admin_client.post(reverse(self.CHANGE_URL, args=(config.pk,)), data=self.form_data())

        assert response.status_code == HTTPStatus.FOUND, response.content.decode()
        config.refresh_from_db()
        assert config.access_token == "saved-token"
        assert config.is_active

    def test_cannot_enable_without_token(self, admin_client: AdminClient) -> None:
        config = WhatsAppSettings.load()

        response = admin_client.post(reverse(self.CHANGE_URL, args=(config.pk,)), data=self.form_data())

        assert response.status_code == HTTPStatus.OK  # form redisplayed with an error
        config.refresh_from_db()
        assert not config.is_enabled

    def test_send_test_message(self, admin_client: AdminClient, mocker: MockerFixture) -> None:
        config = WhatsAppSettings.load()
        config.phone_number_id = "123456789"
        config.access_token = "token"
        config.template_name = "verification_code"
        config.test_phone_number = "237690000000"
        config.save()
        post: MagicMock = mocker.patch("whimo.common.whatsapp.requests.post")
        post.return_value.status_code = 200
        post.return_value.json.return_value = {"messages": [{"id": "wamid.test"}]}

        url = reverse("admin:db_whatsappsettings_send_test_message", args=(config.pk,))
        response = admin_client.get(url)

        assert response.status_code == HTTPStatus.FOUND
        assert post.call_args.kwargs["json"]["to"] == "237690000000"
        config.refresh_from_db()
        assert config.last_test_at is not None
        assert "wamid.test" in config.last_test_status
