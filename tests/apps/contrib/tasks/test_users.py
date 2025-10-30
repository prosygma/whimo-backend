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
