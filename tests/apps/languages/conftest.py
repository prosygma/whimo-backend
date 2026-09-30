from collections.abc import Iterator

import pytest
from django.utils.translation import trans_real

from whimo.languages import services
from whimo.languages.models import Language


@pytest.fixture(autouse=True)
def reset_translations() -> Iterator[None]:
    services._applied_messages.clear()
    trans_real._translations.clear()
    yield
    services._applied_messages.clear()
    trans_real._translations.clear()


@pytest.fixture(autouse=True)
def builtin_languages(db: None) -> None:
    """The languages as migration 0002 creates them, whatever later migrations changed."""
    Language.objects.exclude(code__in=("en", "fr", "es")).delete()
    for position, code in enumerate(("en", "fr", "es"), start=1):
        Language.objects.filter(code=code).update(
            is_enabled=True, is_default=code == "en", position=position, translations={}, version=1
        )
    services.clear_cache()
