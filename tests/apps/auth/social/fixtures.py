from typing import Callable
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from whimo.auth.social.schemas.dto import OAuthUserInfo


@pytest.fixture
def mock_parse_id_token(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.auth.social.service.OAuthService._parse_id_token")


@pytest.fixture
def mock_id_token(mock_parse_id_token: MagicMock) -> Callable[[str], None]:
    def parse_id_token(email: str) -> None:
        userinfo = OAuthUserInfo(email=email, email_verified=True)
        mock_parse_id_token.return_value = userinfo.model_dump()

    return parse_id_token


@pytest.fixture
def mock_parse_code(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("whimo.auth.social.service.OAuthService._parse_code")


@pytest.fixture
def mock_code(mock_parse_code: MagicMock) -> Callable[[str], None]:
    def parse_code(email: str) -> None:
        userinfo = OAuthUserInfo(email=email, email_verified=True)
        mock_parse_code.return_value = userinfo.model_dump()

    return parse_code
