from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_EMAIL, USER_PASSWORD, USER_PHONE
from whimo.auth.registration.schemas.requests import RegistrationRequest
from whimo.db.enums import GadgetType
from whimo.db.models import Gadget, User

pytestmark = [pytest.mark.django_db]


class TestRegistration:
    URL = reverse("registration")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "email": USER_EMAIL,
            "phone": USER_PHONE,
            "password": USER_PASSWORD,
        }
        sanitized_request = RegistrationRequest(**request_data)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CREATED, response_json
        assert response_json == snapshot

        assert User.objects.exists()
        assert Gadget.objects.filter(identifier=sanitized_request.email, type=GadgetType.EMAIL).exists()
        assert Gadget.objects.filter(identifier=sanitized_request.phone, type=GadgetType.PHONE).exists()

    def test_only_phone(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "phone": USER_PHONE,
            "password": USER_PASSWORD,
        }
        sanitized_request = RegistrationRequest(**request_data)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CREATED, response_json
        assert response_json == snapshot

        assert User.objects.exists()
        assert Gadget.objects.filter(identifier=sanitized_request.phone, type=GadgetType.PHONE).exists()

    def test_only_email(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "email": USER_EMAIL,
            "password": USER_PASSWORD,
        }
        sanitized_request = RegistrationRequest(**request_data)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CREATED, response_json
        assert response_json == snapshot

        assert User.objects.exists()
        assert Gadget.objects.filter(identifier=sanitized_request.email, type=GadgetType.EMAIL).exists()

    def test_invalid_email(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "email": USER_PHONE,
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_email_already_exists(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create(email=True)
        request_data = {
            "email": gadget.identifier,
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT, response_json
        assert response_json == snapshot

        assert User.objects.exists()

    def test_phone_already_exists(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create(phone=True)
        request_data = {
            "phone": gadget.identifier,
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT, response_json
        assert response_json == snapshot

    def test_no_phone_or_email(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "password": USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        assert not User.objects.exists()
        assert not Gadget.objects.exists()
