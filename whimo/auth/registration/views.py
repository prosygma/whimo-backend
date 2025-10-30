from typing import Any

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.auth.registration.schemas.requests import RegistrationRequest
from whimo.auth.registration.schemas.responses import RegisteredResponse
from whimo.auth.registration.services import RegistrationService
from whimo.common.throttling import AuthThrottle


class RegistrationView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [AuthThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = RegistrationRequest.parse(request)
        RegistrationService.register(payload)
        return RegisteredResponse().as_response()
