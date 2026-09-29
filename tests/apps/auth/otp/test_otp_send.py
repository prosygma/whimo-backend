import time
from http import HTTPStatus
from unittest.mock import MagicMock, patch

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
from whimo.db.enums import GadgetType, OTPChannel

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
        gadgets = GadgetFactory.create_batch(6, type=GadgetType.EMAIL)

        # Act & Assert - Test within rate limit
        with patch(
            "whimo.auth.otp.services.verify_gadget.VerifyGadgetService.send_otp_code", return_value=OTPChannel.EMAIL
        ):
            for i, gadget in enumerate(gadgets[:5]):
                response = client.post(path=self.URL, data={"identifier": gadget.identifier})
                assert response.status_code == HTTPStatus.OK, f"Request {i + 1} should succeed"

            # Act - Exceed rate limit
            response = client.post(path=self.URL, data={"identifier": gadgets[5].identifier})
            response_json = response.json()

            # Assert
            assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
            assert response_json == snapshot

    def test_identifier_cooldown(
        self,
        client: APIClient,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        request_data = {"identifier": gadget.identifier}

        # Act
        client.post(path=self.URL, data=request_data)
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot
        mock_otp_send_mail.assert_called_once()

    def test_identifier_cooldown_normalized_identifier(
        self,
        client: APIClient,
        mock_otp_send_sms: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        # Act
        client.post(path=self.URL, data={"identifier": gadget.identifier})
        response = client.post(path=self.URL, data={"identifier": f"+{gadget.identifier}"})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot
        mock_otp_send_sms.assert_called_once()

    def test_identifier_cooldown_does_not_affect_others(
        self,
        client: APIClient,
        mock_otp_send_mail: MagicMock,
    ) -> None:
        # Arrange
        gadgets = GadgetFactory.create_batch(2, type=GadgetType.EMAIL)

        # Act
        client.post(path=self.URL, data={"identifier": gadgets[0].identifier})
        response = client.post(path=self.URL, data={"identifier": gadgets[1].identifier})
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert mock_otp_send_mail.call_count == len(gadgets)

    def test_identifier_hourly_limit(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        request_data = {"identifier": gadget.identifier}
        attempts = 5
        clock = [time.time()]
        mocker.patch("rest_framework.throttling.SimpleRateThrottle.timer", side_effect=lambda: clock[0])

        # Act & Assert - Test within hourly limit
        for i in range(attempts):
            response = client.post(path=self.URL, data=request_data)
            assert response.status_code == HTTPStatus.OK, f"Request {i + 1} should succeed"
            clock[0] += 61

        # Act - Exceed hourly limit
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.TOO_MANY_REQUESTS, response_json
        assert response_json == snapshot
        assert mock_otp_send_mail.call_count == attempts

    @override_settings(
        SMS_TELNYX_API_KEY="test_api_key",
        SMS_TELNYX_SENDER_ID="WHIMO",
        SMS_TELNYX_MESSAGING_PROFILE_ID="test_profile_id",
    )
    def test_sms_task(
        self,
        client: APIClient,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.PHONE)

        mocker.patch("whimo.contrib.tasks.users.telnyx.Telnyx")

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
