from pydantic import field_validator

from whimo.common.schemas.base import BaseRequest
from whimo.common.validators.auth import normalize_email, normalize_phone, validate_password


class BaseIdentifierRequest(BaseRequest):
    identifier: str

    @field_validator("identifier", mode="before")
    def normalize_identifier(cls, identifier: str) -> str:
        try:
            return normalize_email(identifier)
        except ValueError:
            return normalize_phone(identifier)


class OTPVerifyRequest(BaseIdentifierRequest):
    code: str


class OTPSendRequest(BaseIdentifierRequest):
    captcha_token: str | None = None


class PasswordResetSendRequest(BaseIdentifierRequest):
    captcha_token: str | None = None


class PasswordResetCheckRequest(BaseIdentifierRequest):
    code: str


class PasswordResetVerifyRequest(BaseIdentifierRequest):
    code: str
    password: str

    @field_validator("password", mode="before")
    def validate_password(cls, password: str) -> str:
        return validate_password(password)
