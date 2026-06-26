from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import BadRequest


class InvalidOTPCodeError(BadRequest):
    message = _("Invalid or expired verification code")
    code = "otp.invalid_code"
