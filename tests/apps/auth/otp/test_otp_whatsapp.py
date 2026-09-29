from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.urls import reverse

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.db.enums import GadgetType, OTPChannel
from whimo.db.models import WhatsAppSettings

pytestmark = [pytest.mark.django_db]

SEND_URLS = [reverse("otp_send"), reverse("password_reset_send")]


class TestOTPWhatsApp:
    @pytest.mark.parametrize("url", SEND_URLS)
    @pytest.mark.usefixtures("whatsapp_enabled")
    def test_phone_code_goes_through_whatsapp_when_enabled(
        self,
        client: APIClient,
        mock_otp_send_sms: MagicMock,
        mock_otp_send_whatsapp: MagicMock,
        url: str,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        # Act
        response = client.post(path=url, data={"identifier": gadget.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json["channel"] == OTPChannel.WHATSAPP
        mock_otp_send_sms.assert_not_called()
        mock_otp_send_whatsapp.assert_called_once()
        kwargs = mock_otp_send_whatsapp.call_args.kwargs
        assert kwargs["recipient"] == gadget.identifier
        assert kwargs["code"].isdigit()

    @pytest.mark.parametrize("url", SEND_URLS)
    def test_phone_code_goes_through_sms_when_incomplete(
        self,
        client: APIClient,
        whatsapp_enabled: WhatsAppSettings,
        mock_otp_send_sms: MagicMock,
        mock_otp_send_whatsapp: MagicMock,
        url: str,
    ) -> None:
        # Arrange: enabled but without a token is not active
        whatsapp_enabled.access_token = ""
        whatsapp_enabled.save()
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        # Act
        response = client.post(path=url, data={"identifier": gadget.identifier})

        # Assert
        assert response.json()["channel"] == OTPChannel.SMS
        mock_otp_send_sms.assert_called_once()
        mock_otp_send_whatsapp.assert_not_called()

    @pytest.mark.usefixtures("whatsapp_enabled")
    def test_email_code_is_not_affected(
        self,
        client: APIClient,
        mock_otp_send_mail: MagicMock,
        mock_otp_send_whatsapp: MagicMock,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)

        # Act
        response = client.post(path=reverse("otp_send"), data={"identifier": gadget.identifier})

        # Assert
        assert response.json()["channel"] == OTPChannel.EMAIL
        mock_otp_send_mail.assert_called_once()
        mock_otp_send_whatsapp.assert_not_called()

    @pytest.mark.usefixtures("whatsapp_enabled")
    def test_language_of_the_request_is_forwarded(
        self,
        client: APIClient,
        mock_otp_send_whatsapp: MagicMock,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        # Act
        client.post(path=reverse("otp_send"), data={"identifier": gadget.identifier}, HTTP_ACCEPT_LANGUAGE="fr-FR")

        # Assert
        assert mock_otp_send_whatsapp.call_args.kwargs["language"].lower() == "fr-fr"
