from collections.abc import Iterator

import pytest
from django.utils.translation import trans_real

from whimo.languages import services


@pytest.fixture(autouse=True)
def reset_translations() -> Iterator[None]:
    services._applied_messages.clear()
    trans_real._translations.clear()
    yield
    services._applied_messages.clear()
    trans_real._translations.clear()
