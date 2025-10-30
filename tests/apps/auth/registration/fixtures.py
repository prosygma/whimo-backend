from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_create_username(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.db.models.users.CustomUserManager.create_username")
