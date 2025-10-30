from http import HTTPStatus
from unittest.mock import Mock

import factory
import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from whimo.db.enums import GadgetType
from whimo.users.views import ProfileDeleteView

pytestmark = [pytest.mark.django_db]


class TestUsersProfileDelete:
    URL = reverse("users_profile")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        GadgetFactory.create_batch(size=len(GadgetType), user=user, type=factory.Iterator(GadgetType))

        client.login(user)

        # Act
        response = client.delete(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        user.refresh_from_db()
        assert user.is_deleted
        assert user.gadgets.count() == 0

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.delete(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot


class TestProfileDeleteView:
    def test_delete_method_direct(self) -> None:
        # Arrange
        user = UserFactory.create()
        view = ProfileDeleteView()
        request = Mock()
        request.user = user

        # Act
        response = view.delete(request)

        # Assert
        assert response.status_code == HTTPStatus.OK
        user.refresh_from_db()
        assert user.is_deleted
