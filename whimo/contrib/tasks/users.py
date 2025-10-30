import logging
import uuid
from http import HTTPStatus
from urllib.parse import urlencode

import requests
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
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
