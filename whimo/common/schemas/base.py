import types
from collections import defaultdict
from typing import Any, Generic, Type, TypeVar, get_args, get_origin

from django.utils.translation import gettext_lazy as _
from django_stubs_ext import StrPromise
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic.fields import FieldInfo
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.errors import ApiError

T = TypeVar("T")
R = TypeVar("R", bound="BaseRequest")


def is_list_type(field_type: FieldInfo | None) -> bool:
    if field_type is None:
        return False

    origin = get_origin(field_type.annotation)
    if origin is list:
        return True

    if origin is types.UnionType:
        for arg in get_args(field_type.annotation):
            if get_origin(arg) is list:
                return True

    return False


class BaseRequest(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    @classmethod
    def parse(cls: Type[R], request: Request, from_query_params: bool = False) -> R:
        data = request.query_params if from_query_params else request.data
        parsed = {
            key: data.getlist(key)  # type: ignore
            if from_query_params and is_list_type(cls.model_fields.get(key))
            else data.get(key)
            for key in data
        }
        return cls.model_validate(parsed)


class PaginationRequest(BaseRequest):
    page: int = 1
    page_size: int = 20


class BaseResponse(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    message: StrPromise | str | None = None
    status: int
    success: bool = True

    @property
    def exclude_fields(self) -> set[str]:
        exclude_fields = {"status"}
        if not self.message:
            exclude_fields.add("message")
        return exclude_fields

    def as_response(self, status_code: int | None = None, by_alias: bool = False, **kwargs: Any) -> Response:
        data = self.model_dump(exclude=self.exclude_fields, by_alias=by_alias)
        response_status = status_code if status_code is not None else self.status
        return Response(data=data, status=response_status, **kwargs)  # type: ignore


class DataResponse(BaseResponse, Generic[T]):
    status: int = status.HTTP_200_OK
    data: T


class MessageResponse(BaseResponse):
    message: StrPromise
    status: int = status.HTTP_200_OK


class Pagination(BaseModel):
    count: int
    page: int
    page_size: int
    next_page: int | None = None
    previous_page: int | None = None
    total_pages: int


class PaginatedDataResponse(DataResponse, Generic[T]):
    data: T
    pagination: Pagination


class ErrorResponse(BaseResponse):
    code: str
    errors: dict | None = None
    success: bool = False

    @property
    def exclude_fields(self) -> set[str]:
        exclude_fields = super().exclude_fields
        if not self.errors:
            exclude_fields.add("errors")
        return exclude_fields


class ApiErrorResponse(ErrorResponse):
    @classmethod
    def parse(cls, exc: ApiError) -> "ErrorResponse":
        return cls(
            message=exc.message,
            status=exc.status,
            code=exc.code,
            errors=exc.errors,
        )


class DRFErrorResponse(ErrorResponse):
    @classmethod
    def parse(cls, exc: APIException) -> "DRFErrorResponse":
        detail = exc.detail or exc.default_detail
        message = detail["detail"] if isinstance(detail, dict) else detail
        rendered = message if isinstance(message, StrPromise) else str(message)

        return cls(message=rendered, status=exc.status_code, code=f"drf.{exc.default_code}")


class PydanticErrorResponse(ErrorResponse):
    code: str = "pydantic.validation_error"
    status: int = status.HTTP_400_BAD_REQUEST

    @classmethod
    def parse(cls, exc: ValidationError) -> "PydanticErrorResponse":
        errors = defaultdict(list)
        for error in exc.errors():
            loc = ", ".join(str(loc) for loc in error["loc"])
            errors[loc].append(error["msg"])

        message = (
            "\n".join(f"{loc}: {', '.join(errors)}" for loc, errors in errors.items()) if errors else _("Bad Request")
        )

        return cls(errors=errors, message=message)
