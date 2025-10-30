from uuid import UUID

from pydantic import BaseModel, field_validator

from whimo.common.validators.auth import normalize_email, normalize_phone


class BaseModelDTO(BaseModel):
    id: UUID


class CreateGadgetDTO(BaseModel):
    email: str | None = None
    phone: str | None = None

    @field_validator("phone", mode="before")
    def normalize_phone(cls, phone: str | None) -> str | None:
        return normalize_phone(phone) if phone else None

    @field_validator("email", mode="before")
    def normalize_email(cls, email: str | None) -> str | None:
        return normalize_email(email) if email else None
