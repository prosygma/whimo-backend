from decimal import Decimal
from http import HTTPStatus
from uuid import UUID

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion

from tests.factories.transactions import create_conversion
from tests.factories.users import UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME
from tests.helpers.utils import queries_to_str
from whimo.common.schemas.base import DataResponse
from whimo.transactions.schemas.dto import ConversionTransactionDTO

pytestmark = [pytest.mark.django_db]


class TestConversionDetail:
    URL = "transactions_conversion_detail"

    def test_success(self, client: APIClient, freezer: FrozenDateTimeFactory, snapshot: SnapshotAssertion) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        conversion_input, main_output, side_output = create_conversion(
            user,
            UUID(int=1),
            inputs=[Decimal(1000)],
            outputs=[Decimal(850), Decimal(150)],
        )

        client.login(user)

        # Act
        with CaptureQueriesContext(connection) as queries:
            response = client.get(path=reverse(self.URL, args=(UUID(int=1),)))
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot

        data_response = DataResponse[ConversionTransactionDTO](**response_json)
        assert data_response.data.group_id == UUID(int=1)
        assert [item.id for item in data_response.data.inputs] == [conversion_input.id]
        assert [item.id for item in data_response.data.outputs] == [main_output.id, side_output.id]

        # Queries:
        # 1. select user
        # 2. select gadgets
        # 3. select conversion rows
        assert len(queries) == 3, queries_to_str(queries)  # noqa: PLR2004 Magic value used in comparison

    def test_other_users_conversion(self, client: APIClient) -> None:
        # Arrange
        owner = UserFactory.create()
        create_conversion(owner, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        client.login(UserFactory.create())

        # Act
        response = client.get(path=reverse(self.URL, args=(UUID(int=1),)))

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response.json()

    def test_unknown_conversion(self, client: APIClient) -> None:
        # Arrange
        client.login(UserFactory.create())

        # Act
        response = client.get(path=reverse(self.URL, args=(UUID(int=1),)))

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response.json()
