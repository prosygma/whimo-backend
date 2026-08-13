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
