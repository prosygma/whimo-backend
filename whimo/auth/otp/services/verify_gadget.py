from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from whimo.auth.otp.constances import OTP_CACHE_KEY
from whimo.auth.otp.schemas.errors import InvalidOTPCodeError
from whimo.auth.otp.schemas.requests import OTPSendRequest, OTPVerifyRequest
from whimo.auth.otp.services.base import BaseOTPService
from whimo.common.schemas.errors import NotFound
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget


@dataclass(slots=True)
class VerifyGadgetService:
    @staticmethod
    def send_otp_code(payload: OTPSendRequest) -> None:
        try:
            gadget = Gadget.objects.get(identifier=payload.identifier)
        except Gadget.DoesNotExist as err:
            raise NotFound(errors={"gadget": [payload.identifier]}) from err

        cache_key = OTP_CACHE_KEY.format(identifier=gadget.identifier)
        code = BaseOTPService.generate_otp_code(cache_key)

        BaseOTPService.send_otp_code(code, GadgetType(gadget.type), gadget.identifier)

    @staticmethod
    def verify_otp_code(payload: OTPVerifyRequest) -> None:
        is_mock_code = settings.OTP_MOCK_CODE and payload.code == settings.OTP_MOCK_CODE
        cache_key = OTP_CACHE_KEY.format(identifier=payload.identifier)
        if cache.get(cache_key) != payload.code and not is_mock_code:
            raise InvalidOTPCodeError

        cache.delete(cache_key)

        try:
            gadget = Gadget.objects.get(identifier=payload.identifier)
        except Gadget.DoesNotExist as err:
            raise NotFound(errors={"gadget": [payload.identifier]}) from err

        gadget.is_verified = True
        gadget.save(update_fields=["updated_at", "is_verified"])
