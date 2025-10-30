from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import USER_PASSWORD

NEW_USER_PASSWORD = "N3w-S3cr3t-P455w0rd"

pytestmark = [pytest.mark.django_db]


class TestUsersProfilePasswordChange:
    URL = reverse("users_profile_password_change")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": NEW_USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(NEW_USER_PASSWORD)
        assert not user.check_password(USER_PASSWORD)

    def test_invalid_current_password(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": "WrongPassword123",
            "new_password": NEW_USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)
        assert not user.check_password(NEW_USER_PASSWORD)

    def test_invalid_new_password_too_short(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": "Short1",
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_invalid_new_password_no_uppercase(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": "invalidpassword1",
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_invalid_new_password_no_lowercase(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": "INVALIDPASSWORD1",
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_invalid_new_password_no_digit(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": "InvalidPassword",
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_missing_current_password(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "new_password": NEW_USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_missing_new_password(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_same_passwords(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(password=USER_PASSWORD)

        request_data = {
            "current_password": USER_PASSWORD,
            "new_password": USER_PASSWORD,
        }

        client.login(user)

        # Act
        response = client.patch(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.check_password(USER_PASSWORD)

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.patch(path=self.URL)
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
