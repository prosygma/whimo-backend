from typing import Any

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.auth.jwt.schemas.requests import TokenObtainPairRequest, TokenRefreshRequest
from whimo.auth.jwt.schemas.responses import AuthorizedResponse
from whimo.auth.jwt.services import JWTService
from whimo.common.throttling import AuthThrottle


class TokenObtainPairView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = TokenObtainPairRequest.parse(request)
        token_pair = JWTService.obtain_token_pair(payload)
        return AuthorizedResponse(data=token_pair).as_response()


class TokenRefreshView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = TokenRefreshRequest.parse(request)
        token_pair = JWTService.refresh_token_pair(payload)
        return AuthorizedResponse(data=token_pair).as_response()
