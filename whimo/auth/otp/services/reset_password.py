from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from whimo.auth.otp.constances import PASSWORD_RESET_CACHE_KEY
from whimo.auth.otp.schemas.errors import InvalidOTPCodeError
from whimo.auth.otp.schemas.requests import PasswordResetSendRequest, PasswordResetVerifyRequest
from whimo.auth.otp.services.base import BaseOTPService
from whimo.common.schemas.errors import NotFound
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget


@dataclass(slots=True)
class ResetPasswordService:
    @staticmethod
    def send_otp_code(payload: PasswordResetSendRequest) -> None:
        try:
            gadget = Gadget.objects.get(identifier=payload.identifier)
        except Gadget.DoesNotExist as err:
            raise NotFound(errors={"gadget": [payload.identifier]}) from err

        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=payload.identifier)
        code = BaseOTPService.generate_otp_code(cache_key)

        BaseOTPService.send_otp_code(code, GadgetType(gadget.type), payload.identifier)

    @staticmethod
    def check_otp_code(identifier: str, code: str, delete: bool = False) -> None:
        is_mock_code = settings.OTP_MOCK_CODE and code == settings.OTP_MOCK_CODE
        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=identifier)
        if cache.get(cache_key) != code and not is_mock_code:
            raise InvalidOTPCodeError

        if delete:
            cache.delete(cache_key)

    @staticmethod
    def verify_otp_code(payload: PasswordResetVerifyRequest) -> None:
        ResetPasswordService.check_otp_code(payload.identifier, payload.code, delete=True)

        try:
            gadget = Gadget.objects.select_related("user").get(identifier=payload.identifier)
        except Gadget.DoesNotExist as err:
            raise NotFound(errors={"gadget": [payload.identifier]}) from err

        gadget.user.set_password(payload.password)
        gadget.user.save()
