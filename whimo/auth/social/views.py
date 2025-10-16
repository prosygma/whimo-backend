from typing import Any

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.auth.jwt.schemas.responses import AuthorizedResponse
from whimo.auth.social.schemas.dto import OAuthProvider
from whimo.auth.social.schemas.requests import OAuthCodeRequest, OAuthIdTokenRequest
from whimo.auth.social.service import OAuthService
from whimo.common.throttling import AuthThrottle
from whimo.common.utils import get_user_model

User = get_user_model()


class GoogleLoginView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OAuthIdTokenRequest.parse(request)
        token_pair = OAuthService.authorize_id_token(payload, OAuthProvider.GOOGLE)
        return AuthorizedResponse(data=token_pair).as_response()


class AppleLoginView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OAuthIdTokenRequest.parse(request)
        token_pair = OAuthService.authorize_id_token(payload, OAuthProvider.APPLE)
        return AuthorizedResponse(data=token_pair).as_response()


class GoogleWebLoginView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OAuthCodeRequest.parse(request)
        token_pair = OAuthService.authorize_code(payload, OAuthProvider.GOOGLE)
        return AuthorizedResponse(data=token_pair).as_response()


class AppleWebLoginView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OAuthCodeRequest.parse(request)
        token_pair = OAuthService.authorize_code(payload, OAuthProvider.APPLE)
        return AuthorizedResponse(data=token_pair).as_response()
