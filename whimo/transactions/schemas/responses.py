from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import MessageResponse


class TransactionStatusUpdatedResponse(MessageResponse):
    message: StrPromise = _("Transaction status updated")


class TransactionGeodataUpdatedResponse(MessageResponse):
    message: StrPromise = _("Transaction geodata updated")


class TransactionGeodataRequestedResponse(MessageResponse):
    message: StrPromise = _("Missing geodata requested")


class TransactionNotificationResentResponse(MessageResponse):
    message: StrPromise = _("Transaction notification resent")
