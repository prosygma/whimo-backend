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
