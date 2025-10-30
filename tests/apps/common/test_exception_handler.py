from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.helpers.clients import APIClient

pytestmark = [pytest.mark.django_db]


class TestExceptionHandler:
    def test_pydantic_error(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse("registration")

        # Act
        response = client.post(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_drf_error(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse("users_profile")

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_internal_server_error(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        url = reverse("users_profile")

        # Act
        response = client.get(path=url)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
