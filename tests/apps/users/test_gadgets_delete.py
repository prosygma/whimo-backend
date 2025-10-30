from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.utils import queries_to_str
from whimo.db.models import Gadget

pytestmark = [pytest.mark.django_db]


class TestGadgetsDelete:
    URL = reverse("gadgets")

    def test_success_delete_unverified_gadget(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        verified_gadget = GadgetFactory.create(email=True, user=user, is_verified=True)
        unverified_gadget = GadgetFactory.create(phone=True, user=user, is_verified=False)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.delete(path=self.URL, data={"identifier": unverified_gadget.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        assert not Gadget.objects.filter(id=unverified_gadget.id).exists()
        assert Gadget.objects.filter(id=verified_gadget.id).exists()

        # Queries:
        # 1. select user for authentication
        # 2. get gadget for deletion
        # 3. delete gadget
        # 4. update gadget history
        assert len(queries) == 4, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_success_delete_verified_gadget_with_other_verified(
        self, client: APIClient, snapshot: SnapshotAssertion
    ) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        verified_gadget1 = GadgetFactory.create(email=True, user=user, is_verified=True)
        verified_gadget2 = GadgetFactory.create(phone=True, user=user, is_verified=True)

        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={"identifier": verified_gadget1.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        assert not Gadget.objects.filter(id=verified_gadget1.id).exists()
        assert Gadget.objects.filter(id=verified_gadget2.id).exists()

    def test_error_delete_last_verified_gadget(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        verified_gadget = GadgetFactory.create(email=True, user=user, is_verified=True)
        unverified_gadget = GadgetFactory.create(phone=True, user=user, is_verified=False)

        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={"identifier": verified_gadget.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        assert Gadget.objects.filter(id=verified_gadget.id).exists()
        assert Gadget.objects.filter(id=unverified_gadget.id).exists()

    def test_error_delete_nonexistent_gadget(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=True)
        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={"identifier": "nonexistent@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_error_delete_another_users_gadget(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user1 = UserFactory.create(with_gadgets=False)
        user2 = UserFactory.create(with_gadgets=False)

        gadget1 = GadgetFactory.create(email=True, user=user1, is_verified=True)
        GadgetFactory.create(phone=True, user=user1, is_verified=True)
        gadget2 = GadgetFactory.create(email=True, user=user2, is_verified=True)

        client.login(user1)

        # Act
        response = client.delete(path=self.URL, data={"identifier": gadget2.identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

        assert Gadget.objects.filter(id=gadget1.id).exists()
        assert Gadget.objects.filter(id=gadget2.id).exists()

    def test_error_empty_identifier(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=True)
        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={"identifier": ""})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_error_missing_identifier(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=True)
        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.delete(path=self.URL, data={"identifier": "test@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True, with_gadgets=True)
        client.login(user)

        # Act
        response = client.delete(path=self.URL, data={"identifier": "test@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
