from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import MessageResponse


class HealthcheckResponse(MessageResponse):
    message: StrPromise = _("Service is healthy")
