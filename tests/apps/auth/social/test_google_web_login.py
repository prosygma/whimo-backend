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


class TestGoogleWebLogin:
    URL = reverse("google_web_login")

    def test_user_exists(self, client: APIClient, mock_code: MagicMock) -> None:
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_code(gadget.identifier)

        request_data = {
            "code": "some-auth-code",
            "redirect_uri": "http://localhost:3000/oauth/callback",
        }

        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        assert User.objects.count() == 1

    def test_user_does_not_exist(self, client: APIClient, mock_code: MagicMock) -> None:
        mock_code(USER_EMAIL)

        request_data = {
            "code": "some-auth-code",
            "redirect_uri": "http://localhost:3000/oauth/callback",
        }

        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        assert Gadget.objects.filter(identifier=USER_EMAIL, type=GadgetType.EMAIL).exists()
        assert User.objects.count() == 1

    def test_oauth_error(self, client: APIClient, mock_parse_code: MagicMock, snapshot: SnapshotAssertion) -> None:
        mock_parse_code.side_effect = OAuthError

        request_data = {
            "code": "some-auth-code",
            "redirect_uri": "http://localhost:3000/oauth/callback",
        }

        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_oauth_parsing_success(self, client: APIClient, mocker: MockerFixture) -> None:
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)

        mock_oauth = MagicMock()
        mock_google_client = MagicMock()
        mock_google_client.fetch_access_token.return_value = {"access_token": "test-token", "id_token": "test-id-token"}
        mock_google_client.parse_id_token.return_value = {
            "email": gadget.identifier,
            "email_verified": True,
        }
        mock_oauth.google = mock_google_client

        mocker.patch("whimo.auth.social.service.OAuth", return_value=mock_oauth)

        request_data = {
            "code": "valid-code",
            "redirect_uri": "http://localhost:3000/oauth/callback",
            "state": "test-state",
            "nonce": "test-nonce",
        }

        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

        mock_google_client.fetch_access_token.assert_called_once_with(
            code="valid-code",
            redirect_uri="http://localhost:3000/oauth/callback",
            state="test-state",
            nonce="test-nonce",
        )
        mock_google_client.parse_id_token.assert_called_once()

    def test_oauth_parsing_error(self, client: APIClient, mocker: MockerFixture, snapshot: SnapshotAssertion) -> None:
        mock_oauth = MagicMock()
        mock_google_client = MagicMock()
        mock_google_client.fetch_access_token.side_effect = OAuthError
        mock_oauth.google = mock_google_client

        mocker.patch("whimo.auth.social.service.OAuth", return_value=mock_oauth)

        request_data = {
            "code": "invalid-code",
            "redirect_uri": "http://localhost:3000/oauth/callback",
        }

        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
