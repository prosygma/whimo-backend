from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from whimo.auth.otp.constances import OTP_CACHE_KEY
from whimo.db.enums import GadgetType

OTP_CODE = "123456"

pytestmark = [pytest.mark.django_db]


class TestOTPVerify:
    URL = reverse("otp_verify")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gadget = GadgetFactory.create(user=user)

        cache_key = OTP_CACHE_KEY.format(user_id=gadget.user_id, identifier=gadget.identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        gadget.refresh_from_db()
        assert gadget.is_verified

    @override_settings(OTP_MOCK_CODE=OTP_CODE)
    def test_mock_otp(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gadget = GadgetFactory.create(user=user)

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        gadget.refresh_from_db()
        assert gadget.is_verified

    def test_invalid_code(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gadget = GadgetFactory.create(user=user)

        invalid_code = OTP_CODE[::-1]
        request_data = {
            "identifier": gadget.identifier,
            "code": invalid_code,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        gadget.refresh_from_db()
        assert not gadget.is_verified

    def test_no_code_in_cache(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        gadget = GadgetFactory.create(user=user)

        request_data = {
            "identifier": gadget.identifier,
            "code": OTP_CODE,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

        gadget.refresh_from_db()
        assert not gadget.is_verified

    def test_gadget_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create()
        identifier = "john@whimo.com"

        cache_key = OTP_CACHE_KEY.format(user_id=user.id, identifier=identifier)
        cache.set(cache_key, OTP_CODE)

        request_data = {
            "identifier": identifier,
            "code": OTP_CODE,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL, is_verified=False)
        request_data = {"identifier": gadget.identifier, "code": "123456"}

        # Act & Assert - Test within rate limit
        with patch("whimo.auth.otp.services.verify_gadget.VerifyGadgetService.verify_otp_code"):
            for _i in range(5):
                response = client.post(path=self.URL, data=request_data)
                assert response.status_code in [HTTPStatus.OK, HTTPStatus.BAD_REQUEST]

            # Act - Exceed rate limit
            response = client.post(path=self.URL, data=request_data)
            response_json = response.json()

            # Assert
            assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
            assert response_json == snapshot
