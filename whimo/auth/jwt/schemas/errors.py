from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import Forbidden, Unauthorized


class TokenNotValidError(Unauthorized):
    message = _("Token is invalid")
    code = "jwt.token_not_valid"


class AuthenticationFailedError(Unauthorized):
    message = _("No active account found with the given credentials")
    code = "jwt.authentication_failed"


class NoVerifiedGadgetError(Forbidden):
    message = _("No verified gadget found")
    code = "jwt.no_verified_gadget"
