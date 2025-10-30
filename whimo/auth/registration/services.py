from dataclasses import dataclass
from typing import TypeVar
from uuid import UUID

from django.db import transaction
from django.db.models import Q

from whimo.auth.registration.schemas.errors import GadgetAlreadyExistsError
from whimo.common.schemas.dto import CreateGadgetDTO
from whimo.common.utils import get_user_model
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget

T = TypeVar("T", bound=CreateGadgetDTO)
User = get_user_model()


@dataclass(slots=True)
class RegistrationService:
    @staticmethod
    def register(payload: T) -> User:  # type: ignore
        password = getattr(payload, "password", None)
        with transaction.atomic():
            user = User.objects.create_custom_user(password=password)
            RegistrationService._create_gadgets(user.id, payload)

        return user

    @staticmethod
    def _create_gadgets(user_id: UUID, request: T) -> None:
        if Gadget.objects.filter(Q(identifier=request.email) | Q(identifier=request.phone)).exists():
            raise GadgetAlreadyExistsError

        if request.email:
            Gadget.objects.create(user_id=user_id, type=GadgetType.EMAIL, identifier=request.email)

        if request.phone:
            Gadget.objects.create(user_id=user_id, type=GadgetType.PHONE, identifier=request.phone)
