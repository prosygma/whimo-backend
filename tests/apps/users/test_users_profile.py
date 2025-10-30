from http import HTTPStatus
from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.common.schemas.errors import NotFound
from whimo.users.schemas.dto import UserDTO
from whimo.users.schemas.requests import PasswordChangeRequest
from whimo.users.services.users import UsersService

pytestmark = [pytest.mark.django_db]


class TestUsersProfile:
    URL = reverse("users_profile")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        GadgetFactory(email=True, user=user)
        GadgetFactory(phone=True, user=user)

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[UserDTO](**response_json)
        assert data_response.data.id == user.id
        assert data_response.data.username == user.username

        # Queries:
        # 1. select user
        # 2. select user
        # 3. select gadgets
        assert len(queries) == 3, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_get_user_not_found(self) -> None:
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFound):
            UsersService.get_user(user_id=non_existent_id)

    def test_change_password_user_not_found(self) -> None:
        # Arrange
        non_existent_id = uuid4()
        payload = PasswordChangeRequest(current_password="oldpass", new_password="NewPassword123!")

        # Act & Assert
        with pytest.raises(NotFound):
            UsersService.change_password(user_id=non_existent_id, payload=payload)

    def test_delete_profile_user_not_found(self) -> None:
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFound):
            UsersService.delete_profile(user_id=non_existent_id)
