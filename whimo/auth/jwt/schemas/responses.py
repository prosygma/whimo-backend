from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise

from whimo.common.schemas.base import DataResponse


class AuthorizedResponse(DataResponse):
    message: StrPromise = _("Authorized")
