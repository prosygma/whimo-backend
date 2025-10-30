from http import HTTPStatus

import pytest
from django.urls import reverse
from syrupy import SnapshotAssertion

from tests.helpers.clients import APIClient

pytestmark = [pytest.mark.django_db]


class TestServicesHealthcheck:
    URL = reverse("system_healthcheck")

    def test_success(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot
