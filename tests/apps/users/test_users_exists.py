from http import HTTPStatus

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.utils import queries_to_str

pytestmark = [pytest.mark.django_db]


class TestUsersExists:
    URL = reverse("users_exists")

    def test_an_active_user_exists(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        recipient = UserFactory.create()

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL, data={"username": recipient.username})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot
        assert response_json["data"]["exists"] is True

        # Queries:
        # 1. select user for authentication
        # 2. check username existence
        assert len(queries) == 2, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_an_unknown_user_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        client.login(UserFactory.create())

        # Act
        response = client.get(path=self.URL, data={"username": "deadbeef"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot
        assert response_json["data"]["exists"] is False

    def test_a_deleted_user_does_not_exist(self, client: APIClient) -> None:
        # Arrange
        recipient = UserFactory.create(is_deleted=True)

        client.login(UserFactory.create())

        # Act
        response = client.get(path=self.URL, data={"username": recipient.username})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json["data"]["exists"] is False

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL, data={"username": "deadbeef"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot
