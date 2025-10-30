from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion
from syrupy.filters import props

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_EMAIL, USER_PHONE
from whimo.db.models import Gadget
from whimo.users.schemas.requests import GadgetCreateRequest

pytestmark = [pytest.mark.django_db]


class TestGadgetsCreate:
    URL = reverse("gadgets")

    def test_success_create_email(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        payload = {"email": USER_EMAIL}
        request = GadgetCreateRequest(**payload)

        # Act
        response = client.post(path=self.URL, data=payload)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        assert Gadget.objects.filter(user_id=user.id, identifier=request.email).exists()

    def test_success_create_phone(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        payload = {"phone": USER_PHONE}
        request = GadgetCreateRequest(**payload)

        # Act
        response = client.post(path=self.URL, data=payload)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        assert Gadget.objects.filter(user_id=user.id, identifier=request.phone).exists()

    def test_error_gadget_already_exists(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        existing = GadgetFactory.create(email=True, user=user, is_verified=True)
        client.login(user)

        # Act
        response = client.post(path=self.URL, data={"email": existing.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT, response_json
        assert response_json == snapshot

    def test_error_both_identifiers_provided(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.post(path=self.URL, data={"email": USER_EMAIL, "phone": USER_PHONE})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_error_missing_identifiers(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.post(path=self.URL, data={})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.post(path=self.URL, data={"email": USER_EMAIL})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True, with_gadgets=False)
        client.login(user)

        # Act
        response = client.post(path=self.URL, data={"email": USER_EMAIL})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
