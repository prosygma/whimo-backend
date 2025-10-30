from enum import StrEnum

from pydantic import BaseModel


class OAuthUserInfo(BaseModel):
    email: str
    email_verified: bool


class OAuthProvider(StrEnum):
    GOOGLE = "google"
    APPLE = "apple"
