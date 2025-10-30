from pydantic import field_validator, model_validator

from whimo.common.schemas.base import BaseRequest
from whimo.common.schemas.dto import CreateGadgetDTO
from whimo.common.validators.auth import normalize_email, normalize_phone, validate_password
from whimo.db.enums import GadgetType
from whimo.users.schemas.errors import ExactlyOneIdentifierRequiredError


class GadgetExistsRequest(BaseRequest):
    identifier: str

    @field_validator("identifier", mode="before")
    def normalize_identifier(cls, identifier: str) -> str:
        try:
            return normalize_email(identifier)
        except ValueError:
            return normalize_phone(identifier)


class GadgetDeleteRequest(BaseRequest):
    identifier: str

    @field_validator("identifier", mode="before")
    def normalize_identifier(cls, identifier: str) -> str:
        try:
            return normalize_email(identifier)
        except ValueError:
            return normalize_phone(identifier)


class GadgetCreateRequest(BaseRequest, CreateGadgetDTO):
    @model_validator(mode="after")
    def validate_identifier(self) -> "GadgetCreateRequest":
        if self.email is not None and self.phone is not None:
            raise ExactlyOneIdentifierRequiredError

        if self.email is None and self.phone is None:
            raise ExactlyOneIdentifierRequiredError

        return self

    @property
    def identifier(self) -> str:
        identifier = self.email or self.phone
        if not identifier:
            raise ExactlyOneIdentifierRequiredError
        return identifier

    @property
    def type(self) -> GadgetType:
        return GadgetType.EMAIL if self.email else GadgetType.PHONE


class PasswordChangeRequest(BaseRequest):
    current_password: str
    new_password: str

    @field_validator("new_password", mode="before")
    def validate_password(cls, password: str) -> str:
        return validate_password(password)
