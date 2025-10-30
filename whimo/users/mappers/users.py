from dataclasses import dataclass

from whimo.common.utils import get_user_model
from whimo.users.mappers.gadgets import GadgetsMapper
from whimo.users.schemas.dto import UserDTO

User = get_user_model()


@dataclass(slots=True)
class UsersMapper:
    @staticmethod
    def to_dto(user: User, with_gadgets: bool = True) -> UserDTO:  # type: ignore
        gadgets_dto = GadgetsMapper.to_dto_list(entities=user.gadgets_list) if with_gadgets else []  # type: ignore

        return UserDTO(
            id=user.id,  # type: ignore
            username=user.username,  # type: ignore
            gadgets=gadgets_dto,
        )
