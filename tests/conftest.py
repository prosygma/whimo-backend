import time
from collections.abc import Iterator

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.db import connections
from faker import Faker
from pytest_django.fixtures import SettingsWrapper
from pytest_django.plugin import DjangoDbBlocker
from pytest_mock import MockerFixture

from whimo.db.models import (
    Balance,
    Commodity,
    CommodityGroup,
    HarvestSeason,
    Notification,
    NotificationSettings,
    Transaction,
)
from whimo.languages import services
from whimo.languages.models import Language

pytest_plugins = [
    # helpers
    "tests.helpers.clients",
    # factories
    "tests.factories.balances",
    "tests.factories.commodities",
    "tests.factories.conversions",
    "tests.factories.harvest_seasons",
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


@pytest.fixture(scope="session")
def django_db_setup(  # pytest-django overrides by fixture name, the param must be named this
    django_db_setup: None,  # noqa: ARG001
    django_db_blocker: DjangoDbBlocker,
) -> None:
    # "test_mode" mirrors the "default" test database (see DATABASES in settings.py),
    # so pytest-django never migrates it on its own - do it here, once per session.
    with django_db_blocker.unblock():
        call_command("migrate", database="test_mode", verbosity=0, interactive=False)


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
def reset_harvest_seasons() -> None:
    HarvestSeason.objects.all().delete()


@pytest.fixture(autouse=True)
def reset_commodities(reset_harvest_seasons: None) -> None:  # noqa: ARG001
    Commodity.objects.all().delete()
    CommodityGroup.objects.all().delete()


@pytest.fixture(autouse=True)
def reset_test_mode_activity(request: pytest.FixtureRequest) -> Iterator[None]:
    # transaction=True tests commit for real instead of rolling back, so leftover
    # test_mode rows from one test are otherwise still there for the next one.
    marker = request.node.get_closest_marker("django_db")
    uses_test_mode = bool(marker) and "test_mode" in (marker.kwargs.get("databases") or ())
    if uses_test_mode:
        Transaction.objects.using("test_mode").all().delete()
        Balance.objects.using("test_mode").all().delete()
        Notification.objects.using("test_mode").all().delete()
        NotificationSettings.objects.using("test_mode").all().delete()

    yield

    # Leaving this connection open blocks Django from flushing/destroying the
    # shared physical database at teardown ("accessed by other users").
    if uses_test_mode:
        connections["test_mode"].close()


@pytest.fixture(autouse=True)
def disable_captcha(settings: SettingsWrapper) -> None:
    settings.CAPTCHA_TURNSTILE_SECRET_KEY = ""


@pytest.fixture(autouse=True)
def fix_throttling_freeze(mocker: MockerFixture) -> None:
    mocker.patch("rest_framework.throttling.SimpleRateThrottle.timer", return_value=time.time())
