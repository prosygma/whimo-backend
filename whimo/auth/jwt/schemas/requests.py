from pydantic import field_validator

from whimo.common.schemas.base import BaseRequest
from whimo.common.validators.auth import normalize_email, normalize_phone


class TokenObtainPairRequest(BaseRequest):
    username: str
    password: str

    @field_validator("username", mode="before")
    def normalize_username(cls, username: str) -> str:
        try:
            return normalize_email(username)
        except ValueError:
            return normalize_phone(username)


class TokenRefreshRequest(BaseRequest):
    refresh: str
