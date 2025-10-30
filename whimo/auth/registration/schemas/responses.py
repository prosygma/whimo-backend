from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise
from rest_framework import status

from whimo.common.schemas.base import MessageResponse


class RegisteredResponse(MessageResponse):
    status: int = status.HTTP_201_CREATED
    message: StrPromise = _("Registered")
