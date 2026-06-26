import logging
import uuid
from http import HTTPStatus
from urllib.parse import urlencode

import plivo
import requests
import telnyx
from celery import current_app
from django.conf import settings
from django.core.mail import send_mail
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


def _send_sms_via_gateway(recipient: str, message: str) -> None:
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


def _send_sms_via_plivo(recipient: str, message: str) -> None:
    client = plivo.RestClient(settings.SMS_PLIVO_AUTH_ID, settings.SMS_PLIVO_AUTH_TOKEN)

    try:
        response = client.messages.create(
            src=settings.SMS_PLIVO_SENDER_ID,
            dst=recipient.strip(),
            text=message,
        )
    except Exception as exc:
        logger.error("Plivo error sending SMS to %s: %s", recipient, exc)
        raise Exception(f"Plivo SMS error: {exc}") from exc

    logger.info("SMS %s to %s sent successfully: %s", message, recipient, response.message_uuid)


def _send_sms_via_telnyx(recipient: str, message: str) -> None:
    client = telnyx.Telnyx(api_key=settings.SMS_TELNYX_API_KEY)

    try:
        if settings.SMS_TELNYX_MESSAGING_PROFILE_ID:
            response = client.messages.send(
                from_=settings.SMS_TELNYX_SENDER_ID,
                to=recipient.strip(),
                text=message,
                messaging_profile_id=settings.SMS_TELNYX_MESSAGING_PROFILE_ID,
            )
        else:
            response = client.messages.send(
                from_=settings.SMS_TELNYX_SENDER_ID,
                to=recipient.strip(),
                text=message,
            )
    except Exception as exc:
        logger.error("Telnyx error sending SMS to %s: %s", recipient, exc)
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

    if settings.SMS_PROVIDER == "plivo":
        _send_sms_via_plivo(recipient, message)
    elif settings.SMS_PROVIDER == "telnyx":
        _send_sms_via_telnyx(recipient, message)
    else:
        _send_sms_via_gateway(recipient, message)


@current_app.task(
    autoretry_for=[Exception],
    retry_backoff=True,
    max_retries=3,
)
def send_email(recipients: list[str], subject: str, message: str) -> None:
    logger.info("Sending email %s to %s", subject, ", ".join(recipients))
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
