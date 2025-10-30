import time

import pytest
from django.core.cache import cache
from faker import Faker
from pytest_mock import MockerFixture

from whimo.db.models import Commodity, CommodityGroup

pytest_plugins = [
    # helpers
    "tests.helpers.clients",
    # factories
    "tests.factories.commodities",
    "tests.factories.notifications",
    "tests.factories.transactions",
    "tests.factories.users",
    # fixtures
    "tests.apps.auth.otp.fixtures",
    "tests.apps.auth.registration.fixtures",
    "tests.apps.auth.social.fixtures",
    "tests.apps.contrib.tasks.fixtures",
    "tests.apps.transactions.fixtures",
]


@pytest.fixture(autouse=True)
def reset_faker() -> None:
    Faker.seed(0)


@pytest.fixture(autouse=True)
def reset_cache() -> None:
    cache.clear()


@pytest.fixture(autouse=True)
def reset_commodities() -> None:
    Commodity.objects.all().delete()
    CommodityGroup.objects.all().delete()


@pytest.fixture(autouse=True)
def fix_throttling_freeze(mocker: MockerFixture) -> None:
    mocker.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=time.time())
