from pydantic import field_validator, model_validator

from whimo.auth.registration.schemas.errors import EmailOrPhoneRequiredError
from whimo.common.schemas.base import BaseRequest
from whimo.common.schemas.dto import CreateGadgetDTO
from whimo.common.validators.auth import validate_password


class RegistrationRequest(BaseRequest, CreateGadgetDTO):
    password: str

    @field_validator("password", mode="before")
    def validate_password(cls, password: str) -> str:
        return validate_password(password)

    @model_validator(mode="after")
    def validate_gadgets(self) -> "RegistrationRequest":
        if not self.email and not self.phone:
            raise EmailOrPhoneRequiredError

        return self
