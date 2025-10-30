from http import HTTPStatus
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.auth.otp.constances import OTP_CACHE_KEY
from whimo.contrib.tasks import send_sms
from whimo.db.enums import GadgetType

pytestmark = [pytest.mark.django_db]


class TestOTPSend:
    URL = reverse("otp_send")

    @pytest.mark.parametrize("gadget_type", GadgetType)
    def test_success(
        self,
        client: APIClient,
        mock_otp_send_mail: MagicMock,
        mock_otp_send_sms: MagicMock,
        gadget_type: GadgetType,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        mock_otp_send_mail.return_value = None
        mock_otp_send_sms.return_value = None

        gadget = GadgetFactory.create(type=gadget_type)

        request_data = {
            "identifier": gadget.identifier,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        cache_key = OTP_CACHE_KEY.format(user_id=gadget.user_id, identifier=gadget.identifier)
        assert cache.get(cache_key) is not None

    def test_gadget_does_not_exist(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        request_data = {
            "identifier": "nonexistent@example.com",
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_throttling(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        request_data = {"identifier": gadget.identifier}

        # Act & Assert - Test within rate limit
        with patch("whimo.auth.otp.services.verify_gadget.VerifyGadgetService.send_otp_code"):
            for i in range(5):
                response = client.post(path=self.URL, data=request_data)
                assert response.status_code == HTTPStatus.OK, f"Request {i + 1} should succeed"

            # Act - Exceed rate limit
            response = client.post(path=self.URL, data=request_data)
            response_json = response.json()

            # Assert
            assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
            assert response_json == snapshot

    @override_settings(
        SMS_GATEWAY_ENABLED=True,
        SMS_GATEWAY_PORT=80,
        SMS_GATEWAY_USERNAME="test_user",
        SMS_GATEWAY_PASSWORD="test_pass",
        SMS_GATEWAY_SENDER_ID="WHIMO",
        SMS_GATEWAY_BASE_URL="http://smsgw.test.local:80/message",
    )
    def test_sms_task(
        self,
        client: APIClient,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        mock_response = Mock()
        mock_response.status_code = 200
        mocker.patch("whimo.contrib.tasks.users.requests.get", return_value=mock_response)

        def mock_sms_delay(recipient: str, message: str) -> None:
            return send_sms(recipient, message)

        mocker.patch("whimo.contrib.tasks.users.send_sms.delay", side_effect=mock_sms_delay)

        request_data = {
            "identifier": gadget.identifier,
        }

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json

        cache_key = OTP_CACHE_KEY.format(user_id=gadget.user_id, identifier=gadget.identifier)
        assert cache.get(cache_key) is not None
