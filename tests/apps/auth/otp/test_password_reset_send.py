from http import HTTPStatus
from unittest.mock import MagicMock

import pytest
from django.core.cache import cache
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.factories.users import GadgetFactory
from tests.helpers.clients import APIClient
from whimo.auth.otp.constances import PASSWORD_RESET_CACHE_KEY
from whimo.db.enums import GadgetType

pytestmark = [pytest.mark.django_db]


class TestPasswordResetSend:
    URL = reverse("password_reset_send")

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

        cache_key = PASSWORD_RESET_CACHE_KEY.format(user_id=gadget.user_id, identifier=gadget.identifier)
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
