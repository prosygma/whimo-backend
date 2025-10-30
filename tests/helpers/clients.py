import pytest
from django.test import Client
from rest_framework.test import APIClient as TestAPIClient
from rest_framework_simplejwt.tokens import AccessToken

from tests.helpers.constants import ADMIN_PASSWORD
from whimo.db.models import User


class APIClient(TestAPIClient):
    def login(self, user: User) -> bool:  # type: ignore
        token = AccessToken.for_user(user)
        self.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return True


@pytest.fixture
def client() -> APIClient:
    return APIClient()


class AdminClient(Client):
    def login(self, user: User) -> bool:  # type: ignore
        return super().login(username=user.username, password=ADMIN_PASSWORD)


@pytest.fixture
def admin_client() -> AdminClient:
    return AdminClient()
