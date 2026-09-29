from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from whimo.db.models import WhatsAppSettings


@pytest.fixture
def mock_otp_send_mail(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_email.delay")


@pytest.fixture
def mock_otp_send_sms(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_sms.delay")


@pytest.fixture
def mock_otp_send_whatsapp(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_whatsapp_otp.delay")


@pytest.fixture
def whatsapp_enabled() -> WhatsAppSettings:
    config = WhatsAppSettings.load()
    config.is_enabled = True
    config.phone_number_id = "123456789"
    config.access_token = "test-token"
    config.template_name = "verification_code"
    config.save()
    return config
