from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import MessageResponse


class OTPVerifiedResponse(MessageResponse):
    message: StrPromise = _("Gadget verified")


class OTPSentResponse(MessageResponse):
    message: StrPromise = _("Verification code sent")


class PasswordResetSentResponse(MessageResponse):
    message: StrPromise = _("Reset code sent")


class PasswordResetOTPValidResponse(MessageResponse):
    message: StrPromise = _("Verification code is valid")


class PasswordResetResponse(MessageResponse):
    message: StrPromise = _("Password reset")
