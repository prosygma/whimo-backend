from math import ceil
from typing import TYPE_CHECKING

from django.core.cache import caches
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

from whimo.common.schemas.errors import TooManyRequests
from whimo.common.validators.auth import normalize_email, normalize_phone

if TYPE_CHECKING:  # pragma: no cover
    from rest_framework.views import APIView


class OTPThrottle(AnonRateThrottle):
    scope = "otp"
    cache = caches["default"]


class IdentifierRateThrottle(SimpleRateThrottle):
    cache = caches["default"]

    def get_cache_key(self, request: Request, _view: "APIView") -> str | None:
        identifier = request.data.get("identifier") if isinstance(request.data, dict) else None
        if not isinstance(identifier, str):
            return None

        try:
            normalized = normalize_email(identifier)
        except ValueError:
            normalized = normalize_phone(identifier)

        return self.cache_format % {"scope": self.scope, "ident": normalized}

    def throttle_failure(self) -> bool:
        raise TooManyRequests(retry_after=ceil(self.wait() or 0))


class OTPIdentifierCooldownThrottle(IdentifierRateThrottle):
    scope = "otp_identifier_cooldown"


class OTPIdentifierThrottle(IdentifierRateThrottle):
    scope = "otp_identifier"


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
