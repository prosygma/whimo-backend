from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_send_mail(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_mail")


@pytest.fixture
def mock_telnyx_client(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.telnyx.Telnyx")
