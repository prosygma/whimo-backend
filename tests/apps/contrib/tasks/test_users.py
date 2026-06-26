from unittest.mock import MagicMock

import pytest
from django.conf import settings
from django.test import override_settings

from whimo.contrib.tasks.users import send_email, send_sms

pytestmark = [pytest.mark.django_db]


class TestUsersTasks:
    def test_send_email_task(self, mock_send_mail: MagicMock) -> None:
        # Arrange
        recipients = ["user1@example.com", "user2@example.com"]
        subject = "Test Email Subject"
        message = "Test email message content"

        # Act
        send_email(recipients, subject, message)

        # Assert
        mock_send_mail.assert_called_once_with(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )

    @override_settings(
        SMS_GATEWAY_ENABLED=True,
        SMS_GATEWAY_PORT=80,
        SMS_GATEWAY_USERNAME="test_user",
        SMS_GATEWAY_PASSWORD="test_pass",
        SMS_GATEWAY_SENDER_ID="WHIMO",
        SMS_GATEWAY_BASE_URL="http://smsgw.test.local:80/message",
    )
    def test_send_sms_task(self, mock_requests_get: MagicMock) -> None:
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response

        recipient = "1234567890"
        message = "Test SMS message"

        send_sms(recipient, message)

        mock_requests_get.assert_called_once()

    @override_settings(
        SMS_PROVIDER="plivo",
        SMS_PLIVO_AUTH_ID="test_auth_id",
        SMS_PLIVO_AUTH_TOKEN="test_auth_token",
        SMS_PLIVO_SENDER_ID="WHIMO",
    )
    def test_send_sms_via_plivo(self, mock_plivo_client: MagicMock) -> None:
        recipient = "+1234567890"
        message = "Test SMS message"

        send_sms(recipient, message)

        mock_plivo_client.assert_called_once_with("test_auth_id", "test_auth_token")
        mock_plivo_client.return_value.messages.create.assert_called_once_with(
            src="WHIMO",
            dst=recipient,
            text=message,
        )

    @override_settings(
        SMS_PROVIDER="telnyx",
        SMS_TELNYX_API_KEY="test_api_key",
        SMS_TELNYX_SENDER_ID="WHIMO",
        SMS_TELNYX_MESSAGING_PROFILE_ID="",
    )
    def test_send_sms_via_telnyx(self, mock_telnyx_client: MagicMock) -> None:
        recipient = "+1234567890"
        message = "Test SMS message"

        send_sms(recipient, message)

        mock_telnyx_client.assert_called_once_with(api_key="test_api_key")
        mock_telnyx_client.return_value.messages.send.assert_called_once_with(
            from_="WHIMO",
            to=recipient,
            text=message,
        )
