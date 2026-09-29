from unittest.mock import MagicMock

import pytest
import requests
from pytest_mock import MockerFixture

from whimo.common.whatsapp import WhatsAppClient, WhatsAppError, WhatsAppTemporaryError
from whimo.contrib.tasks.users import send_whatsapp_otp
from whimo.db.models import WhatsAppSettings

pytestmark = [pytest.mark.django_db]


@pytest.fixture
def config() -> WhatsAppSettings:
    return WhatsAppSettings(
        is_enabled=True,
        api_version="v21.0",
        phone_number_id="123456789",
        access_token="test-token",
        template_name="verification_code",
    )


@pytest.fixture
def mock_post(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.common.whatsapp.requests.post")


def response(status: int, body: dict) -> MagicMock:
    mock = MagicMock(status_code=status)
    mock.json.return_value = body
    return mock


class TestWhatsAppClient:
    def test_sends_authentication_template(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        # Arrange
        mock_post.return_value = response(200, {"messages": [{"id": "wamid.1"}]})

        # Act
        message_id = WhatsAppClient(config).send_otp("+237690000000", "123456", "fr-fr")

        # Assert
        assert message_id == "wamid.1"
        url = mock_post.call_args.args[0]
        kwargs = mock_post.call_args.kwargs
        assert url == "https://graph.facebook.com/v21.0/123456789/messages"
        assert kwargs["headers"] == {"Authorization": "Bearer test-token"}
        payload = kwargs["json"]
        assert payload["to"] == "237690000000"
        assert payload["template"]["name"] == "verification_code"
        assert payload["template"]["language"] == {"code": "fr"}
        body, button = payload["template"]["components"]
        assert body["parameters"] == [{"type": "text", "text": "123456"}]
        assert button["sub_type"] == "url"
        assert button["parameters"] == [{"type": "text", "text": "123456"}]

    @pytest.mark.parametrize(
        ("language", "expected"),
        [("en-us", "en_US"), ("fr-fr", "fr"), ("fr", "fr"), ("es-mx", "es"), ("de-de", "en_US"), (None, "en_US")],
    )
    def test_template_language(self, config: WhatsAppSettings, language: str | None, expected: str) -> None:
        assert config.template_language(language) == expected

    def test_client_error_is_final(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        mock_post.return_value = response(400, {"error": {"message": "Template name does not exist"}})

        with pytest.raises(WhatsAppError, match="Template name does not exist"):
            WhatsAppClient(config).send_otp("237690000000", "123456")

    def test_server_error_is_temporary(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        mock_post.return_value = response(503, {})

        with pytest.raises(WhatsAppTemporaryError):
            WhatsAppClient(config).send_otp("237690000000", "123456")

    def test_network_error_is_temporary(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.ConnectionError("down")

        with pytest.raises(WhatsAppTemporaryError):
            WhatsAppClient(config).send_otp("237690000000", "123456")


class TestSendWhatsAppOTPTask:
    def test_sends_with_saved_settings(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        config.save()
        mock_post.return_value = response(200, {"messages": [{"id": "wamid.1"}]})

        send_whatsapp_otp("237690000000", "123456", "en-us")

        mock_post.assert_called_once()

    def test_does_nothing_when_not_configured(self, mock_post: MagicMock) -> None:
        send_whatsapp_otp("237690000000", "123456", "en-us")

        mock_post.assert_not_called()

    def test_rejected_message_is_not_retried(self, config: WhatsAppSettings, mock_post: MagicMock) -> None:
        config.save()
        mock_post.return_value = response(401, {"error": {"message": "Invalid OAuth access token"}})

        send_whatsapp_otp("237690000000", "123456")  # must not raise

        mock_post.assert_called_once()
