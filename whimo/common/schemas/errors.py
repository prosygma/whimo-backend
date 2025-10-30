from typing import ClassVar

from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise
from rest_framework import status


class ApiError(Exception):
    message: ClassVar[StrPromise]
    code: ClassVar[str]
    status: ClassVar[int]
    errors: dict | None = None


class BadRequest(ApiError):
    message = _("Bad Request")
    code = "api.bad_request"
    status = status.HTTP_400_BAD_REQUEST


class Unauthorized(ApiError):
    message = _("Unauthorized")
    code = "api.unauthorized"
    status = status.HTTP_401_UNAUTHORIZED


class Forbidden(ApiError):
    message = _("Forbidden")
    code = "api.forbidden"
    status = status.HTTP_403_FORBIDDEN


class NotFound(ApiError):
    message = _("Object Not Found")
    code = "api.not_found"
    status = status.HTTP_404_NOT_FOUND

    def __init__(self, errors: dict | None = None) -> None:
        self.errors = errors


class Conflict(ApiError):
    message = _("Conflict")
    code = "api.conflict"
    status = status.HTTP_409_CONFLICT


class InternalServerError(ApiError):
    message = _("Internal Server Error")
    code = "api.internal"
    status = status.HTTP_500_INTERNAL_SERVER_ERROR
