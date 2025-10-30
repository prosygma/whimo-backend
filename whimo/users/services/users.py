from dataclasses import dataclass
from uuid import UUID

from django.db import transaction

from whimo.common.schemas.errors import NotFound
from whimo.common.utils import get_user_model
from whimo.users.schemas.errors import InvalidCurrentPasswordError
from whimo.users.schemas.requests import PasswordChangeRequest

User = get_user_model()


@dataclass(slots=True)
class UsersService:
    @staticmethod
    def get_user(user_id: UUID) -> User:  # type: ignore
        try:
            return User.objects.prefetch_gadgets(include_unverified=True).get(pk=user_id)
        except User.DoesNotExist as err:
            raise NotFound(errors={"user": [user_id]}) from err

    @staticmethod
    def change_password(user_id: UUID, payload: PasswordChangeRequest) -> None:
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as err:
            raise NotFound(errors={"user": [user_id]}) from err

        if not user.check_password(payload.current_password):
            raise InvalidCurrentPasswordError

        user.set_password(payload.new_password)
        user.save()

    @staticmethod
    def delete_profile(user_id: UUID) -> User:  # type: ignore
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist as err:
            raise NotFound(errors={"user": [user_id]}) from err

        with transaction.atomic():
            user.is_deleted = True
            user.save(update_fields=["updated_at", "is_deleted"])
            user.gadgets.all().delete()

        return user
