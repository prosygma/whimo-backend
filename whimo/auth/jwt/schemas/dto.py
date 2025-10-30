from pydantic import BaseModel


class AccessRefreshTokenDTO(BaseModel):
    access: str
    refresh: str
