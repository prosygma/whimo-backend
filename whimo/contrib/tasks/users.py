import logging
import uuid
from http import HTTPStatus
from urllib.parse import urlencode

import requests
from celery import current_app
from django.conf import settings
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SMSMessageParams(BaseModel):
    user: str
    password: str = Field(serialization_alias="pass")
    sender: str = Field(serialization_alias="from")
    to: str
    tag: str
    text: str
    id: str
    dlrreq: str


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_sms(recipient: str, message: str) -> None:
    logger.info("Sending SMS %s to %s", message, recipient)

    params = SMSMessageParams(
        user=settings.SMS_GATEWAY_USERNAME,
        password=settings.SMS_GATEWAY_PASSWORD,
        sender=settings.SMS_GATEWAY_SENDER_ID,
        to=recipient.strip().lstrip("+"),
        tag=settings.SMS_GATEWAY_DEFAULT_TAG,
        text=message,
        id=str(uuid.uuid4()),
        dlrreq="0",
    )

    query_params = urlencode(params.model_dump(by_alias=True))
    url = f"{settings.SMS_GATEWAY_BASE_URL}?{query_params}"

    try:
        response = requests.get(url=url, timeout=settings.SMS_GATEWAY_TIMEOUT)
    except requests.exceptions.ConnectTimeout as exc:
        raise Exception("SMS connection timeout") from exc

    if response.status_code != HTTPStatus.OK:
        logger.error(
            "SMS gateway server error for %s: status=%d, response=%s",
            url,
            response.status_code,
            response.text,
        )
        raise Exception(f"SMS gateway error: {response.status_code}")

    logger.info("SMS %s to %s sent successfully: %s", message, recipient, response.text)


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
