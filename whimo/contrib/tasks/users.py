import logging
from http import HTTPStatus

import requests
import telnyx
from celery import current_app
from django.conf import settings

from whimo.common.whatsapp import WhatsAppClient, WhatsAppError, WhatsAppTemporaryError
from whimo.db.models import WhatsAppSettings

logger = logging.getLogger(__name__)


def _send_sms_via_telnyx(recipient: str, message: str) -> None:
    client = telnyx.Telnyx(api_key=settings.SMS_TELNYX_API_KEY)
    destination = f"+{recipient.strip().lstrip('+')}"

    try:
        response = client.messages.send(
            from_=settings.SMS_TELNYX_SENDER_ID,
            to=destination,
            text=message,
            messaging_profile_id=settings.SMS_TELNYX_MESSAGING_PROFILE_ID,
        )
    except Exception as exc:
        raise Exception(f"Telnyx SMS error: {exc}") from exc

    message_id = response.data.id if response.data else None
    logger.info("SMS %s to %s sent successfully: %s", message, recipient, message_id)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_sms(recipient: str, message: str) -> None:
    logger.info("Sending SMS %s to %s", message, recipient)
    _send_sms_via_telnyx(recipient, message)


@current_app.task(
    autoretry_for=[WhatsAppTemporaryError],
    retry_backoff=True,
    max_retries=3,
)
def send_whatsapp_otp(recipient: str, code: str, language: str | None = None) -> None:
    config = WhatsAppSettings.load()
    if not config.is_active:
        logger.error("WhatsApp is not configured; verification code for %s not sent", recipient)
        return

    try:
        message_id = WhatsAppClient(config).send_otp(recipient, code, language)
    except WhatsAppError:
        # Wrong token, template or number: retrying cannot succeed.
        logger.exception("WhatsApp verification code to %s rejected", recipient)
        return

    logger.info("WhatsApp verification code to %s sent: %s", recipient, message_id)


class SendMailError(Exception):
    """The relay refused the message (configuration, sender, content): retrying cannot succeed."""


class SendMailTemporaryError(SendMailError):
    """Network error, rate limit or relay failure: worth retrying."""


@current_app.task(
    autoretry_for=[SendMailTemporaryError],
    retry_backoff=True,
    max_retries=3,
)
def send_email(recipients: list[str], subject: str, message: str) -> None:
    logger.info("Sending email %s to %s", subject, ", ".join(recipients))

    if not settings.SENDMAIL_API_KEY:
        raise SendMailError("SendMail API key not configured (SENDMAIL_API_KEY)")
    if not settings.SENDMAIL_API_FROM_EMAIL:
        raise SendMailError("SendMail sender not configured (SENDMAIL_API_FROM_EMAIL)")

    # The relay chooses the SMTP transport itself, by profile or by sender domain.
    payload = {
        "message": {
            "from": {
                "email": settings.SENDMAIL_API_FROM_EMAIL,
                "name": settings.SENDMAIL_API_FROM_NAME,
            },
            "to": [{"email": recipient, "name": recipient} for recipient in recipients],
            "cc": settings.SENDMAIL_API_CC,
            "bcc": [],
            "reply_to": settings.SENDMAIL_API_REPLY_TO,
            "subject": subject,
            "body_html": message,
            "body_text": "",
            "attachments": [],
        },
    }
    if settings.SENDMAIL_API_SMTP_PROFILE:
        payload["smtp_profile"] = settings.SENDMAIL_API_SMTP_PROFILE

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # The client provided the auth "key" without specifying the header name.
        # We include both common variants to maximize compatibility.
        "key": settings.SENDMAIL_API_KEY,
        "x-api-key": settings.SENDMAIL_API_KEY,
    }

    try:
        response = requests.post(
            settings.SENDMAIL_API_URL,
            json=payload,
            headers=headers,
            timeout=settings.SENDMAIL_API_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise SendMailTemporaryError(f"SendMail API unreachable: {exc}") from exc

    if response.status_code != HTTPStatus.OK:
        logger.error(
            "SendMail API error: status=%d, response=%s",
            response.status_code,
            " ".join(response.text.split()),
        )
        error_class = (
            SendMailTemporaryError
            if response.status_code >= HTTPStatus.INTERNAL_SERVER_ERROR
            or response.status_code == HTTPStatus.TOO_MANY_REQUESTS
            else SendMailError
        )
        raise error_class(f"SendMail API error: {response.status_code}")

    try:
        body = response.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        body = {}
    result = body.get("result") if isinstance(body.get("result"), dict) else {}

    # In dry-run mode (the relay's default) it answers 200 without sending anything.
    if result.get("sent") is False:
        logger.warning(
            "SendMail API did not send the email: message=%s, message_id=%s, dry_run=%s",
            body.get("message"),
            body.get("message_id"),
            result.get("dry_run"),
        )
        raise SendMailError(f"SendMail API did not send the email: {body.get('message')}")

    logger.info(
        "Email %s to %s sent successfully: %s",
        subject,
        ", ".join(recipients),
        body.get("message_id"),
    )
