from dataclasses import dataclass
from uuid import UUID

from whimo.auth.registration.schemas.errors import GadgetAlreadyExistsError
from whimo.common.schemas.errors import NotFound
from whimo.db.models import Gadget
from whimo.users.schemas.dto import GadgetExistsDTO
from whimo.users.schemas.errors import LastVerifiedGadgetError
from whimo.users.schemas.requests import GadgetCreateRequest


@dataclass(slots=True)
class GadgetsService:
    @staticmethod
    def check_identifier_exists(identifier: str) -> GadgetExistsDTO:
        exists = Gadget.objects.filter(identifier=identifier).exists()
        return GadgetExistsDTO(exists=exists)

    @staticmethod
    def delete_gadget(user_id: UUID, identifier: str) -> None:
        try:
            gadget = Gadget.objects.get(user_id=user_id, identifier=identifier)
        except Gadget.DoesNotExist as err:
            raise NotFound(errors={"gadget": [identifier]}) from err

        if gadget.is_verified:
            remaining_verified_gadgets = Gadget.objects.filter(user_id=user_id, is_verified=True).exclude(id=gadget.id)
            if remaining_verified_gadgets.count() == 0:
                raise LastVerifiedGadgetError

        gadget.delete()

    @staticmethod
    def create_gadget(user_id: UUID, payload: GadgetCreateRequest) -> Gadget:
        if Gadget.objects.filter(identifier=payload.identifier).exists():
            raise GadgetAlreadyExistsError

        return Gadget.objects.create(user_id=user_id, type=payload.type, identifier=payload.identifier)
