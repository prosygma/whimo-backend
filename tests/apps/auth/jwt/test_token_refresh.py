from http import HTTPStatus

import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken
from syrupy import SnapshotAssertion

from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_PASSWORD
from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO
from whimo.common.schemas.base import DataResponse

pytestmark = [pytest.mark.django_db]


class TestTokenRefresh:
    URL = reverse("token_pair_refresh")

    def test_success(self, client: APIClient) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)
        refresh = RefreshToken.for_user(user)

        request_data = {
            "refresh": str(refresh),
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

    def test_invalid_token(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "refresh": "invalid_token_string",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
