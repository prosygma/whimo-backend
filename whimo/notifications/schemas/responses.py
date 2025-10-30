from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import MessageResponse


class NotificationStatusUpdatedResponse(MessageResponse):
    message: StrPromise = _("Notification status updated")


class NotificationSettingsUpdatedResponse(MessageResponse):
    message: StrPromise = _("Notification settings updated")


class DeviceAddedResponse(MessageResponse):
    message: StrPromise = _("Device added")
