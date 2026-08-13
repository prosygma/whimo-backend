from dataclasses import dataclass

import requests
from django.conf import settings

from whimo.common.schemas.errors import InvalidCaptchaError

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
TURNSTILE_VERIFY_TIMEOUT = 5


@dataclass(slots=True)
class CaptchaService:
    @staticmethod
    def verify(token: str | None) -> None:
        if not settings.CAPTCHA_TURNSTILE_SECRET_KEY:
            return

        if not token:
            raise InvalidCaptchaError

        try:
            response = requests.post(
                TURNSTILE_VERIFY_URL,
                data={"secret": settings.CAPTCHA_TURNSTILE_SECRET_KEY, "response": token},
                timeout=TURNSTILE_VERIFY_TIMEOUT,
            )
            response.raise_for_status()
            is_valid = response.json().get("success", False)
        except requests.RequestException as err:
            raise InvalidCaptchaError from err

        if not is_valid:
            raise InvalidCaptchaError
