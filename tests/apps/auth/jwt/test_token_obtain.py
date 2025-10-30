from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_PASSWORD
from whimo.auth.jwt.schemas.dto import AccessRefreshTokenDTO
from whimo.common.schemas.base import DataResponse
from whimo.db.enums import GadgetType

pytestmark = [pytest.mark.django_db]


class TestTokenObtain:
    URL = reverse("token_pair_obtain")

    @pytest.mark.parametrize("gadget_type", GadgetType)
    def test_success(self, client: APIClient, gadget_type: GadgetType) -> None:
        # Arrange
        gadget = GadgetFactory(type=gadget_type, user__password=USER_PASSWORD, is_verified=True)

        request_data = {
            "username": gadget.identifier,
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

    @pytest.mark.parametrize("gadget_type", GadgetType)
    def test_success_normalized_phone(self, client: APIClient, gadget_type: GadgetType) -> None:
        # Arrange
        gadget = GadgetFactory(type=gadget_type, user__password=USER_PASSWORD, identifier="12345678", is_verified=True)

        request_data = {
            "username": f"+{gadget.identifier}",
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        data_response = DataResponse[AccessRefreshTokenDTO](**response_json)
        assert data_response.data.access
        assert data_response.data.refresh

    def test_invalid_credentials(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "username": "invalid_username",
            "password": "invalid_password",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_invalid_password(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory(user__password=USER_PASSWORD)

        request_data = {
            "username": gadget.identifier,
            "password": "invalid_password",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory(user__password=USER_PASSWORD, user__is_deleted=True)

        request_data = {
            "username": gadget.identifier,
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD, with_gadgets=False)
        gadget = GadgetFactory.create(user=user, is_verified=False)

        request_data = {
            "username": gadget.identifier,
            "password": USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gadget = GadgetFactory.create(user=user)
        request_data = {"identifier": gadget.identifier, "password": "testpass"}

        # Act & Assert - Test within rate limit
        for _i in range(20):
            response = client.post(path=self.URL, data=request_data)
            assert response.status_code in [HTTPStatus.OK, HTTPStatus.BAD_REQUEST, HTTPStatus.UNAUTHORIZED]

        # Act - Exceed rate limit
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot
