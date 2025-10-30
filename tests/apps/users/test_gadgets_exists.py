from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.utils import queries_to_str

pytestmark = [pytest.mark.django_db]


class TestGadgetsExists:
    URL = reverse("gadgets_exists")

    def test_success_exists_true(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        identifier = "test@example.com"
        GadgetFactory(email=True, user=user, identifier=identifier)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL, data={"identifier": identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        # Queries:
        # 1. select user for authentication
        # 2. check gadget existence
        assert len(queries) == 2, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_not_found(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL, data={"identifier": "nonexistent@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    def test_empty_identifier_parameter(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL, data={"identifier": ""})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL, data={"identifier": "test@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True, with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL, data={"identifier": "test@example.com"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
