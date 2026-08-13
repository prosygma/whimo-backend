import logging

import telnyx
from celery import current_app
from django.conf import settings
from django.core.mail import send_mail

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
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=False,
    )
