from typing import Any, cast

import factory
import pytest

from tests.factories.base import BaseFactory
from tests.factories.notifications import NotificationSettingsFactory
from tests.helpers.constants import ADMIN_PASSWORD
from whimo.db.enums import GadgetType
from whimo.db.enums.notifications import NotificationType
from whimo.db.models import Gadget, User


class UserFactory(BaseFactory[User]):
    class Meta:
        model = User
        skip_postgeneration_save = True

    class Params:
        superuser = factory.Trait(is_staff=True, is_superuser=True, password=ADMIN_PASSWORD)

    username = factory.Faker("hexify", text="^" * 16)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    password = factory.Faker("password")

    is_deleted = False

    @factory.post_generation
    def _set_password(self, is_created: bool, *_: Any, **__: Any) -> None:
        if not is_created:
            return

        user = cast("User", self)
        user.set_password(user.password)
        user.save()

    @factory.post_generation
    def with_notification_settings(self, is_created: bool, extracted: bool | None, **__: Any) -> None:
        if not is_created or extracted is False:
            return

        NotificationSettingsFactory.create_batch(
            size=len(NotificationType),
            user=self,
            type=factory.Iterator(NotificationType),
        )

    @factory.post_generation
    def with_gadgets(self, is_created: bool, extracted: bool | None, **__: Any) -> None:
        if not is_created or extracted is False:
            return

        user = cast("User", self)
        GadgetFactory.create(user=user, email=True, is_verified=True)
        GadgetFactory.create(user=user, phone=True, is_verified=True)


class GadgetFactory(BaseFactory[Gadget]):
    class Meta:
        model = Gadget

    class Params:
        email = factory.Trait(type=GadgetType.EMAIL, identifier=factory.Faker("email"))
        phone = factory.Trait(type=GadgetType.PHONE, identifier=factory.Faker("numerify", text="###########"))

    user = factory.SubFactory(UserFactory)
    type = factory.Faker("random_element", elements=GadgetType)
    identifier = factory.Faker("numerify", text="###########")
    is_verified = False


@pytest.fixture(autouse=True)
def reset_user_factories() -> None:
    UserFactory.reset_sequence()
    GadgetFactory.reset_sequence()
