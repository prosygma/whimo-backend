from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import MessageResponse


class GadgetExistsResponse(MessageResponse):
    message: StrPromise = _("Gadget exists")


class GadgetDeletedResponse(MessageResponse):
    message: StrPromise = _("Gadget deleted")


class PasswordChangedResponse(MessageResponse):
    message: StrPromise = _("Password changed")


class ProfileDeletedResponse(MessageResponse):
    message: StrPromise = _("Profile deleted")
