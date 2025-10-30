from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import BadRequest, Conflict


class InvalidUpdateStatusError(BadRequest):
    message = _("Invalid update status")


class DeviceAlreadyExistsError(Conflict):
    message = _("Device with this token already exists")
