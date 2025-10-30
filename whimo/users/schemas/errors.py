from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import BadRequest, InternalServerError


class InvalidCurrentPasswordError(BadRequest):
    message = _("Current password is incorrect")
    code = "users.invalid_current_password"


class EmailSendingError(InternalServerError):
    message = _("Email sending error")


class SMSSendingError(InternalServerError):
    message = _("SMS sending error")


class LastVerifiedGadgetError(BadRequest):
    message = _("Cannot delete the last verified gadget")
    code = "users.last_verified_gadget"


class ExactlyOneIdentifierRequiredError(BadRequest):
    message = _("Exactly one identifier must be specified")
