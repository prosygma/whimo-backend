import logging

from pydantic import ValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from whimo.common.schemas.base import ApiErrorResponse, DRFErrorResponse, PydanticErrorResponse
from whimo.common.schemas.errors import ApiError, InternalServerError

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception | type[ApiError], _: dict) -> Response:
    if isinstance(exc, ApiError):
        error = ApiErrorResponse.parse(exc)
    elif isinstance(exc, ValidationError):
        error = PydanticErrorResponse.parse(exc)
    elif isinstance(exc, APIException):
        error = DRFErrorResponse.parse(exc)
    else:
        error = ApiErrorResponse.parse(InternalServerError())

    if error.status >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception(exc)

    return error.as_response()
