from unittest.mock import MagicMock, Mock

import pytest
from django.test import override_settings

from whimo.contrib.tasks.users import send_email, send_sms

pytestmark = [pytest.mark.django_db]


class TestUsersTasks:
    @override_settings(
        SENDMAIL_API_URL="https://sendmail.test.local/send",
        SENDMAIL_API_KEY="test-key",
        SENDMAIL_API_SMTP_AUTH=True,
        SENDMAIL_API_SMTP_PASSWORD="smtp-pass",
    )
    def test_send_email_task(self, mock_requests_post: MagicMock) -> None:
        # Arrange
        recipients = ["user1@example.com", "user2@example.com"]
        subject = "Test Email Subject"
        message = "Test email message content"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests_post.return_value = mock_response

        # Act
        send_email(recipients, subject, message)

        # Assert
        mock_requests_post.assert_called_once()
        _, kwargs = mock_requests_post.call_args
        assert mock_requests_post.call_args.args[0] == "https://sendmail.test.local/send"
        assert kwargs["json"]["message"]["subject"] == subject
        assert kwargs["json"]["message"]["body_html"] == message
        assert [r["email"] for r in kwargs["json"]["message"]["to"]] == recipients

    @override_settings(
        SMS_TELNYX_API_KEY="test_api_key",
        SMS_TELNYX_SENDER_ID="WHIMO",
        SMS_TELNYX_MESSAGING_PROFILE_ID="test_profile_id",
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
            messaging_profile_id="test_profile_id",
        )

    @override_settings(
        SMS_TELNYX_API_KEY="test_api_key",
        SMS_TELNYX_SENDER_ID="WHIMO",
        SMS_TELNYX_MESSAGING_PROFILE_ID="test_profile_id",
    )
    def test_send_sms_via_telnyx_normalizes_recipient(self, mock_telnyx_client: MagicMock) -> None:
        message = "Test SMS message"

        send_sms("1234567890", message)

        mock_telnyx_client.return_value.messages.send.assert_called_once_with(
            from_="WHIMO",
            to="+1234567890",
            text=message,
            messaging_profile_id="test_profile_id",
        )
