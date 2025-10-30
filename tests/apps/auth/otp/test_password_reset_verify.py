from http import HTTPStatus

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.auth.otp.constances import PASSWORD_RESET_CACHE_KEY
from whimo.db.models import User

NEW_USER_PASSWORD = "S3cr3t-Us3r-N3w-P455w0rd"
OTP_CODE = "123456"

pytestmark = [pytest.mark.django_db]


class TestPasswordResetVerify:
    URL = reverse("password_reset_verify")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=gadget.identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
            "password": NEW_USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        user = User.objects.get(id=gadget.user_id)
        assert user.check_password(NEW_USER_PASSWORD)
        assert cache.get(cache_key) is None

    @override_settings(OTP_MOCK_CODE=OTP_CODE)
    def test_mock_otp(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
            "password": NEW_USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        user = User.objects.get(id=gadget.user_id)
        assert user.check_password(NEW_USER_PASSWORD)

    def test_invalid_code(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        invalid_code = OTP_CODE[::-1]
        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=gadget.identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": gadget.identifier,
            "code": invalid_code,
            "password": NEW_USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user = User.objects.get(id=gadget.user_id)
        assert not user.check_password(NEW_USER_PASSWORD)
        assert cache.get(cache_key) == OTP_CODE

    def test_no_code_in_cache(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
            "password": NEW_USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        user = User.objects.get(id=gadget.user_id)
        assert not user.check_password(NEW_USER_PASSWORD)

    def test_gadget_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        identifier = "john@whimo.com"

        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": identifier,
            "code": OTP_CODE,
            "password": NEW_USER_PASSWORD,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot
        assert cache.get(cache_key) is None
