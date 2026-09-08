import logging
from http import HTTPStatus

import requests
import telnyx
from celery import current_app
from django.conf import settings

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
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_email(recipients: list[str], subject: str, message: str) -> None:
    logger.info("Sending email %s to %s", subject, ", ".join(recipients))

    if not settings.SENDMAIL_API_KEY:
        raise Exception("SendMail API key not configured (SENDMAIL_API_KEY)")
    if settings.SENDMAIL_API_SMTP_AUTH and not settings.SENDMAIL_API_SMTP_PASSWORD:
        raise Exception("SendMail SMTP password not configured (SENDMAIL_API_SMTP_PASSWORD)")

    payload = {
        "smtp": {
            "host": settings.SENDMAIL_API_SMTP_HOST,
            "port": settings.SENDMAIL_API_SMTP_PORT,
            "auth": settings.SENDMAIL_API_SMTP_AUTH,
            "username": settings.SENDMAIL_API_SMTP_USERNAME,
            "password": settings.SENDMAIL_API_SMTP_PASSWORD,
            "encryption": settings.SENDMAIL_API_SMTP_ENCRYPTION,
            "auto_tls": settings.SENDMAIL_API_SMTP_AUTO_TLS,
            "timeout": settings.SENDMAIL_API_SMTP_TIMEOUT,
            "debug": settings.SENDMAIL_API_SMTP_DEBUG,
        },
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
            "template": "",
            "template_data": {},
            "attachments": [],
        },
    }

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
    except requests.exceptions.ConnectTimeout as exc:
        raise Exception("SendMail API connection timeout") from exc

    if response.status_code != HTTPStatus.OK:
        logger.error(
            "SendMail API error: status=%d, response=%s",
            response.status_code,
            response.text,
        )
        raise Exception(f"SendMail API error: {response.status_code}")

    logger.info("Email %s to %s sent successfully", subject, ", ".join(recipients))
