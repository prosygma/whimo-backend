from typing import TYPE_CHECKING

from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

if TYPE_CHECKING:
    from rest_framework.request import Request
    from rest_framework.views import APIView


class OTPThrottle(AnonRateThrottle):
    scope = "otp"
    cache = caches["default"]


class AuthThrottle(AnonRateThrottle):
    scope = "auth"
    cache = caches["default"]


class DownloadThrottle(UserRateThrottle):
    scope = "downloads"
    cache = caches["default"]


class DefaultUserThrottle(UserRateThrottle):
    scope = "user"
    cache = caches["default"]


class DefaultAnonThrottle(AnonRateThrottle):
    scope = "anon"
    cache = caches["default"]

    def allow_request(self, request: "Request", view: "APIView") -> bool:
        if request.path == "/api/v1/system/healthcheck/":
            return True
        return super().allow_request(request, view)
