from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_otp_send_mail(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_email.delay")


@pytest.fixture
def mock_otp_send_sms(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_sms.delay")
