from io import BufferedReader
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from tests.helpers.constants import FIXTURES_PATH


@pytest.fixture
def mock_default_storage(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.transactions.services.default_storage")


@pytest.fixture
def mock_get_chain_feature_collection(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.transactions.services.TransactionsService.get_chain_feature_collection")


@pytest.fixture
def geo_json_file() -> BufferedReader:
    geo_json = FIXTURES_PATH / "location_file" / "geo.json"
    return geo_json.open("rb")


@pytest.fixture
def mock_invite_email(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_email.delay")


@pytest.fixture
def mock_invite_sms(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.send_sms.delay")
