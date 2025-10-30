from dataclasses import dataclass

from whimo.db.enums import GadgetType
from whimo.db.models import Gadget
from whimo.users.schemas.dto import GadgetDTO


@dataclass(slots=True)
class GadgetsMapper:
    @staticmethod
    def to_dto(entity: Gadget) -> GadgetDTO:
        return GadgetDTO(
            id=entity.id,
            type=GadgetType(entity.type),
            identifier=entity.identifier,
            is_verified=entity.is_verified,
        )

    @staticmethod
    def to_dto_list(entities: list[Gadget]) -> list[GadgetDTO]:
        return [GadgetsMapper.to_dto(entity) for entity in entities]
