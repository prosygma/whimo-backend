from unittest.mock import MagicMock, Mock

import pytest
from django.test import override_settings

from whimo.contrib.tasks.users import SendMailError, SendMailTemporaryError, send_email, send_sms

pytestmark = [pytest.mark.django_db]

SENT_RESPONSE = {"success": True, "message_id": "mail_1", "result": {"sent": True, "dry_run": False}}


class TestUsersTasks:
    @override_settings(
        SENDMAIL_API_URL="https://sendmail.test.local/send",
        SENDMAIL_API_KEY="test-key",
        SENDMAIL_API_FROM_EMAIL="contact@example.com",
        SENDMAIL_API_SMTP_PROFILE="",
    )
    def test_send_email_task(self, mock_requests_post: MagicMock) -> None:
        # Arrange
        recipients = ["user1@example.com", "user2@example.com"]
        subject = "Test Email Subject"
        message = "Test email message content"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = SENT_RESPONSE
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
        assert kwargs["json"]["message"]["from"]["email"] == "contact@example.com"
        assert "smtp" not in kwargs["json"]
        assert "smtp_profile" not in kwargs["json"]

    @override_settings(
        SENDMAIL_API_KEY="test-key",
        SENDMAIL_API_FROM_EMAIL="contact@example.com",
        SENDMAIL_API_SMTP_PROFILE="camertrace",
    )
    def test_send_email_selects_smtp_profile(self, mock_requests_post: MagicMock) -> None:
        mock_requests_post.return_value = Mock(status_code=200, json=Mock(return_value=SENT_RESPONSE))

        send_email(["user@example.com"], "Subject", "Body")

        assert mock_requests_post.call_args.kwargs["json"]["smtp_profile"] == "camertrace"

    @override_settings(SENDMAIL_API_KEY="test-key", SENDMAIL_API_FROM_EMAIL="")
    def test_send_email_requires_sender(self, mock_requests_post: MagicMock) -> None:
        with pytest.raises(SendMailError, match="SENDMAIL_API_FROM_EMAIL"):
            send_email.run(["user@example.com"], "Subject", "Body")

        mock_requests_post.assert_not_called()

    @pytest.mark.parametrize(
        ("status_code", "error_class"),
        [(400, SendMailError), (429, SendMailTemporaryError), (502, SendMailTemporaryError)],
    )
    @override_settings(SENDMAIL_API_KEY="test-key", SENDMAIL_API_FROM_EMAIL="contact@example.com")
    def test_send_email_error_is_retried_only_when_temporary(
        self,
        mock_requests_post: MagicMock,
        status_code: int,
        error_class: type[Exception],
    ) -> None:
        mock_requests_post.return_value = Mock(status_code=status_code, text='{\n  "error": "x"\n}')

        with pytest.raises(SendMailError) as exc_info:
            send_email.run(["user@example.com"], "Subject", "Body")

        assert type(exc_info.value) is error_class
        assert SendMailTemporaryError in send_email.autoretry_for

    @override_settings(SENDMAIL_API_KEY="test-key", SENDMAIL_API_FROM_EMAIL="contact@example.com")
    def test_send_email_fails_when_relay_is_in_dry_run(self, mock_requests_post: MagicMock) -> None:
        dry_run_response = {
            "success": True,
            "message": "Validation SMTP effectuee en mode dry-run.",
            "message_id": "mail_2",
            "result": {"sent": False, "dry_run": True},
        }
        mock_requests_post.return_value = Mock(status_code=200, json=Mock(return_value=dry_run_response))

        with pytest.raises(SendMailError, match="dry-run") as exc_info:
            send_email.run(["user@example.com"], "Subject", "Body")

        assert type(exc_info.value) is SendMailError

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
