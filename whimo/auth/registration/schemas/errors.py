from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import BadRequest, Conflict


class InvalidEmailError(BadRequest):
    message = _("Invalid email")


class EmailOrPhoneRequiredError(BadRequest):
    message = _("Email address or phone number is required")


class GadgetAlreadyExistsError(Conflict):
    message = _("Gadget with this identifier already exists")
