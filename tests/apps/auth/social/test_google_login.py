from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from authlib.integrations.base_client import OAuthError
from django.urls import reverse
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_EMAIL
from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget, User

pytestmark = [pytest.mark.django_db]


class TestGoogleLogin:
    URL = reverse("google_login")

    def test_user_exists(self, client: APIClient, mock_id_token: MagicMock) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_id_token(gadget.identifier)

        request_data = {
            "id_token": "some-id-token",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        assert User.objects.count() == 1

    def test_user_does_not_exist(self, client: APIClient, mock_id_token: MagicMock) -> None:
        # Arrange
        mock_id_token(USER_EMAIL)

        request_data = {
            "id_token": "some-id-token",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        assert Gadget.objects.filter(identifier=USER_EMAIL, type=GadgetType.EMAIL).exists()
        assert User.objects.count() == 1

    def test_oauth_error(self, client: APIClient, mock_parse_id_token: MagicMock, snapshot: SnapshotAssertion) -> None:
        # Arrange
        mock_parse_id_token.side_effect = OAuthError

        request_data = {
            "id_token": "some-id-token",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_oauth_parsing_success(self, client: APIClient, mocker: MockerFixture) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)

        mock_oauth = MagicMock()
        mock_google_client = MagicMock()
        mock_google_client.parse_id_token.return_value = {
            "email": gadget.identifier,
            "email_verified": True,
        }
        mock_oauth.google = mock_google_client

        mocker.patch("whimo.auth.social.service.OAuth", return_value=mock_oauth)

        request_data = {
            "id_token": "valid-token",
            "nonce": "test-nonce",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        mock_oauth.register.assert_called_once()
        mock_google_client.parse_id_token.assert_called_once_with(token={"id_token": "valid-token"}, nonce="test-nonce")

    def test_oauth_parsing_error(self, client: APIClient, mocker: MockerFixture, snapshot: SnapshotAssertion) -> None:
        # Arrange
        mock_oauth = MagicMock()
        mock_google_client = MagicMock()
        mock_google_client.parse_id_token.side_effect = Exception("Token parsing failed")
        mock_oauth.google = mock_google_client

        mocker.patch("whimo.auth.social.service.OAuth", return_value=mock_oauth)

        request_data = {
            "id_token": "invalid-token",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
