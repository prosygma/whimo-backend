from http import HTTPStatus

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.auth.otp.constances import PASSWORD_RESET_CACHE_KEY

OTP_CODE = "123456"

pytestmark = [pytest.mark.django_db]


class TestPasswordResetCheck:
    URL = reverse("password_reset_check")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=gadget.identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    @override_settings(OTP_MOCK_CODE=OTP_CODE)
    def test_mock_otp(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

    def test_invalid_code(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        invalid_code = OTP_CODE[::-1]
        cache_key = PASSWORD_RESET_CACHE_KEY.format(identifier=gadget.identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": gadget.identifier,
            "code": invalid_code,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_no_code_in_cache(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create()

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
