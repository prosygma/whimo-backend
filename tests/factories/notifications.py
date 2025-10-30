import factory
import pytest
from push_notifications.models import APNSDevice, GCMDevice

from tests.factories.base import BaseFactory
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Notification, NotificationSettings


class NotificationFactory(BaseFactory[Notification]):
    class Meta:
        model = Notification

    status = factory.Faker("random_element", elements=NotificationStatus)
    type = factory.Faker("random_element", elements=NotificationType)
    received_by = factory.SubFactory("tests.factories.users.UserFactory")
    created_by = factory.SubFactory("tests.factories.users.UserFactory")


class NotificationSettingsFactory(BaseFactory[NotificationSettings]):
    class Meta:
        model = NotificationSettings

    user = factory.SubFactory("tests.factories.users.UserFactory")
    type = factory.Faker("random_element", elements=NotificationType)
    is_enabled = True


class GCMDeviceFactory(BaseFactory[GCMDevice]):
    class Meta:
        model = GCMDevice

    user = factory.SubFactory("tests.factories.users.UserFactory")
    registration_id = factory.Faker("numerify", text="###########")


class APNSDeviceFactory(BaseFactory[APNSDevice]):
    class Meta:
        model = APNSDevice

    user = factory.SubFactory("tests.factories.users.UserFactory")
    registration_id = factory.Faker("numerify", text="###########")


@pytest.fixture(autouse=True)
def reset_notifications_factories() -> None:
    NotificationFactory.reset_sequence()
