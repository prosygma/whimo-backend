import secrets
import string
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from whimo.contrib.tasks.users import send_email, send_sms
from whimo.db.enums import GadgetType


@dataclass(slots=True)
class BaseOTPService:
    @staticmethod
    def generate_otp_code(cache_key: str) -> str:
        code = "".join([secrets.choice(string.digits) for _ in range(settings.OTP_LENGTH)])
        cache.set(cache_key, code, timeout=settings.OTP_EXPIRY_MINUTES * 60)
        return code

    @staticmethod
    def send_otp_code(code: str, gadget_type: GadgetType, identifier: str) -> None:
        if gadget_type == GadgetType.EMAIL:
            BaseOTPService._send_otp_email(identifier, code)
        elif gadget_type == GadgetType.PHONE:
            BaseOTPService._send_otp_sms(identifier, code)

    @staticmethod
    def _send_otp_email(email: str, code: str) -> None:
        send_email.delay(
            recipients=[email],
            subject=_("Your verification code"),
            message=_("Your verification code is: %s") % code,
        )

    @staticmethod
    def _send_otp_sms(phone: str, code: str) -> None:
        send_sms.delay(recipient=phone, message=_("Your verification code is: %s") % code)
