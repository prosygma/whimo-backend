from typing import Any

from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.base import DataResponse
from whimo.users.mappers.gadgets import GadgetsMapper
from whimo.users.mappers.users import UsersMapper
from whimo.users.schemas.requests import (
    GadgetCreateRequest,
    GadgetDeleteRequest,
    GadgetExistsRequest,
    PasswordChangeRequest,
)
from whimo.users.schemas.responses import GadgetDeletedResponse, PasswordChangedResponse, ProfileDeletedResponse
from whimo.users.services import GadgetsService, UsersService


class ProfileView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        user = UsersService.get_user(user_id=request.user.id)

        response = UsersMapper.to_dto(user)
        return DataResponse(data=response).as_response()

    def delete(self, request: Request, *_: Any, **__: Any) -> Response:
        UsersService.delete_profile(user_id=request.user.id)
        return ProfileDeletedResponse().as_response()


class ProfilePasswordChangeView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def patch(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = PasswordChangeRequest.parse(request)
        UsersService.change_password(user_id=request.user.id, payload=payload)
        return PasswordChangedResponse().as_response()


class GadgetExistsView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = GadgetExistsRequest.parse(request, from_query_params=True)
        response = GadgetsService.check_identifier_exists(identifier=payload.identifier)
        return DataResponse(data=response).as_response()


class GadgetView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = GadgetCreateRequest.parse(request)
        gadget = GadgetsService.create_gadget(user_id=request.user.id, payload=payload)

        response = GadgetsMapper.to_dto(gadget)
        return DataResponse(data=response).as_response()

    def delete(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = GadgetDeleteRequest.parse(request)
        GadgetsService.delete_gadget(user_id=request.user.id, identifier=payload.identifier)
        return GadgetDeletedResponse().as_response()


class ProfileDeleteView(views.APIView):
    permission_classes = (IsAuthenticated,)

    def delete(self, request: Request, *_: Any, **__: Any) -> Response:
        UsersService.delete_profile(user_id=request.user.id)
        return ProfileDeletedResponse().as_response()
