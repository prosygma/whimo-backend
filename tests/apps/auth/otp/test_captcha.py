from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
import requests
from django.urls import reverse
from pytest_django.fixtures import SettingsWrapper
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.db.enums import GadgetType

pytestmark = [pytest.mark.django_db]


@pytest.fixture(autouse=True)
def enable_captcha(settings: SettingsWrapper) -> None:
    settings.CAPTCHA_TURNSTILE_SECRET_KEY = "test_secret_key"


class TestOTPSendCaptcha:
    URL = reverse("otp_send")

    def test_success(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_post = mocker.patch("whimo.common.captcha.requests.post")
        mock_post.return_value.json.return_value = {"success": True}

        request_data = {"identifier": gadget.identifier, "captcha_token": "valid_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        mock_otp_send_mail.assert_called_once()

    def test_missing_token(
        self,
        client: APIClient,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        request_data = {"identifier": gadget.identifier}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
        mock_otp_send_mail.assert_not_called()

    def test_rejected_token(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_post = mocker.patch("whimo.common.captcha.requests.post")
        mock_post.return_value.json.return_value = {"success": False}

        request_data = {"identifier": gadget.identifier, "captcha_token": "invalid_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
        mock_otp_send_mail.assert_not_called()

    def test_verification_unavailable(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mocker.patch("whimo.common.captcha.requests.post", side_effect=requests.RequestException)

        request_data = {"identifier": gadget.identifier, "captcha_token": "valid_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
        mock_otp_send_mail.assert_not_called()


class TestPasswordResetSendCaptcha:
    URL = reverse("password_reset_send")

    def test_success(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_post = mocker.patch("whimo.common.captcha.requests.post")
        mock_post.return_value.json.return_value = {"success": True}

        request_data = {"identifier": gadget.identifier, "captcha_token": "valid_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        mock_otp_send_mail.assert_called_once()

    def test_rejected_token(
        self,
        client: APIClient,
        mocker: MockerFixture,
        mock_otp_send_mail: MagicMock,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        gadget = GadgetFactory.create(type=GadgetType.EMAIL)
        mock_post = mocker.patch("whimo.common.captcha.requests.post")
        mock_post.return_value.json.return_value = {"success": False}

        request_data = {"identifier": gadget.identifier, "captcha_token": "invalid_token"}

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
        mock_otp_send_mail.assert_not_called()
