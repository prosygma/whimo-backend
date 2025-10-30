from pydantic import BaseModel

from whimo.common.schemas.dto import BaseModelDTO
from whimo.db.enums import GadgetType


class GadgetDTO(BaseModelDTO):
    type: GadgetType
    identifier: str
    is_verified: bool


class UserDTO(BaseModelDTO):
    username: str
    gadgets: list[GadgetDTO]


class GadgetExistsDTO(BaseModel):
    exists: bool
