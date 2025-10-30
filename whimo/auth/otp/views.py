from typing import Any

from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.auth.otp.schemas.requests import (
    OTPSendRequest,
    OTPVerifyRequest,
    PasswordResetCheckRequest,
    PasswordResetSendRequest,
    PasswordResetVerifyRequest,
)
from whimo.auth.otp.schemas.responses import (
    OTPSentResponse,
    OTPVerifiedResponse,
    PasswordResetOTPValidResponse,
    PasswordResetResponse,
    PasswordResetSentResponse,
)
from whimo.auth.otp.services.reset_password import ResetPasswordService
from whimo.auth.otp.services.verify_gadget import VerifyGadgetService
from whimo.common.throttling import OTPThrottle


class OTPSendView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [OTPThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OTPSendRequest.parse(request)
        VerifyGadgetService.send_otp_code(payload)
        return OTPSentResponse().as_response()


class OTPVerifyView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [OTPThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = OTPVerifyRequest.parse(request)
        VerifyGadgetService.verify_otp_code(payload)
        return OTPVerifiedResponse().as_response()


class PasswordResetSendView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [OTPThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = PasswordResetSendRequest.parse(request)
        ResetPasswordService.send_otp_code(payload)
        return PasswordResetSentResponse().as_response()


class PasswordResetCheckView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [OTPThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = PasswordResetCheckRequest.parse(request)
        ResetPasswordService.check_otp_code(payload.identifier, payload.code)
        return PasswordResetOTPValidResponse().as_response()


class PasswordResetVerifyView(views.APIView):
    permission_classes = (AllowAny,)
    throttle_classes = [OTPThrottle]

    def post(self, request: Request, *_: Any, **__: Any) -> Response:
        payload = PasswordResetVerifyRequest.parse(request)
        ResetPasswordService.verify_otp_code(payload)
        return PasswordResetResponse().as_response()
