import time

import pytest
from django.core.cache import cache
from faker import Faker
from pytest_django.fixtures import SettingsWrapper
from pytest_mock import MockerFixture

from whimo.db.models import Commodity, CommodityGroup
from whimo.languages import services
from whimo.languages.models import Language

pytest_plugins = [
    # helpers
    "tests.helpers.clients",
    # factories
    "tests.factories.commodities",
    "tests.factories.conversions",
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
def reset_cache(request: pytest.FixtureRequest) -> None:
    cache.clear()
    # The enabled languages are cached, as in production; load them before the test so that
    # query counts only include the test's own queries.
    if request.node.get_closest_marker("django_db"):
        request.getfixturevalue("db")
        reset_languages()
        services.enabled_languages()


def reset_languages() -> None:
    """The languages as migration languages/0002 creates them, whatever a deployment's own
    migrations changed (default language, disabled ones)."""
    Language.objects.exclude(code__in=("en", "fr", "es")).delete()
    Language.objects.update(is_default=False)  # one default at a time
    for position, code in enumerate(("en", "fr", "es"), start=1):
        Language.objects.filter(code=code).update(
            is_enabled=True, is_default=code == "en", position=position, translations={}, version=1
        )


@pytest.fixture(autouse=True)
def reset_commodities() -> None:
    Commodity.objects.all().delete()
    CommodityGroup.objects.all().delete()


@pytest.fixture(autouse=True)
def disable_captcha(settings: SettingsWrapper) -> None:
    settings.CAPTCHA_TURNSTILE_SECRET_KEY = ""


@pytest.fixture(autouse=True)
def fix_throttling_freeze(mocker: MockerFixture) -> None:
    mocker.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=time.time())
