from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_requests_post(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.requests.post")


@pytest.fixture
def mock_requests_get(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.contrib.tasks.users.requests.get")
