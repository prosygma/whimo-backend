from django.core.cache import caches
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


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
