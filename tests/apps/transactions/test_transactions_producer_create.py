import io
import json
from http import HTTPStatus
from io import BufferedReader
from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from syrupy import SnapshotAssertion
from syrupy.filters import props

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, USER_EMAIL, USER_PHONE
from whimo.db.enums import GadgetType, TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.db.models import Balance, Transaction
from whimo.transactions.schemas.requests import TransactionProducerCreateRequest

pytestmark = [pytest.mark.django_db]


class TestTransactionsProducerCreate:
    URL = reverse("transactions_producer_create")

    @pytest.mark.parametrize("location", TransactionLocation)
    def test_success(  # noqa: PLR0913 Too many arguments in function definition
        self,
        location: TransactionLocation,
        client: APIClient,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": location,
            "transaction_latitude": 0,
            "transaction_longitude": 0,
            "farm_latitude": 1,
            "farm_longitude": 1,
            "is_buying_from_farmer": True,
        }

        if location in {TransactionLocation.FILE, TransactionLocation.QR}:
            request_data["location_file"] = geo_json_file
            mock_default_storage.return_value = Mock()

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.type == TransactionType.PRODUCER
        assert transaction.status == TransactionStatus.ACCEPTED

        assert transaction.commodity_id == UUID(request_data["commodity_id"])  # type: ignore
        assert transaction.volume == request_data["volume"]

        assert transaction.location == request_data["location"]
        assert transaction.farm_latitude == request_data["farm_latitude"]
        assert transaction.farm_longitude == request_data["farm_longitude"]
        assert transaction.transaction_latitude == request_data["transaction_latitude"]
        assert transaction.transaction_longitude == request_data["transaction_longitude"]

        assert transaction.is_buying_from_farmer
        assert not transaction.is_automatic
        assert transaction.expires_at is None

        assert transaction.buyer_id == user.id
        assert transaction.seller_id is None
        assert transaction.created_by_id == user.id

        balance = Balance.objects.get(user=user, commodity=commodity)
        assert balance.volume == request_data["volume"]

    @pytest.mark.parametrize("location", [TransactionLocation.QR, TransactionLocation.GPS])
    def test_full_traceability(  # noqa: PLR0913 Too many arguments in function definition
        self,
        location: TransactionLocation,
        client: APIClient,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": location,
            "latitude": 0,
            "longitude": 0,
            "is_buying_from_farmer": True,
        }

        if location == TransactionLocation.QR:
            request_data["location_file"] = geo_json_file
            mock_default_storage.return_value = Mock()

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.traceability == TransactionTraceability.FULL

    @pytest.mark.parametrize("location", [TransactionLocation.MANUAL, TransactionLocation.FILE])
    def test_conditional_traceability(  # noqa: PLR0913 Too many arguments in function definition
        self,
        location: TransactionLocation,
        client: APIClient,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": location,
            "latitude": 0,
            "longitude": 0,
            "is_buying_from_farmer": True,
        }

        if location == TransactionLocation.FILE:
            request_data["location_file"] = geo_json_file
            mock_default_storage.return_value = Mock()

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.traceability == TransactionTraceability.CONDITIONAL

    def test_partial_traceability(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.traceability == TransactionTraceability.PARTIAL

    def test_incomplete_traceability(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": False,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.traceability == TransactionTraceability.INCOMPLETE

    def test_no_location(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.location is None
        assert transaction.transaction_latitude is None
        assert transaction.transaction_longitude is None

    def test_balance_already_exists(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        initial_volume = 100
        balance = BalanceFactory.create(user=user, commodity=commodity, volume=initial_volume)

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        balance.refresh_from_db()
        assert balance.volume == initial_volume + request_data["volume"]  # type: ignore

    def test_create_recipient_and_send_invite_email(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_create_username: MagicMock,
        mock_invite_email: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "recipient": json.dumps({"email": USER_EMAIL}),
        }

        mock_create_username.return_value = "John Doe"

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.buyer_id == user.id

        mock_invite_email.assert_called_once_with(
            recipients=[USER_EMAIL],
            subject="Welcome to WHIMO!",
            message="You have been invited to Whimo!",
        )

    def test_find_recipient_with_email(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_invite_email: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        GadgetFactory.create(type=GadgetType.EMAIL, identifier=USER_EMAIL)

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "recipient": json.dumps({"email": USER_EMAIL}),
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.buyer_id == user.id

        mock_invite_email.assert_not_called()

    def test_create_recipient_and_send_invite_phone(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_create_username: MagicMock,
        mock_invite_sms: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "recipient": json.dumps({"phone": USER_PHONE}),
        }

        mock_create_username.return_value = "John Doe"

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.buyer_id == user.id

        mock_invite_sms.assert_called_once_with(
            recipient=USER_PHONE.lstrip("+"),
            message="You have been invited to Whimo!",
        )

    def test_find_recipient_with_phone(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_invite_sms: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "recipient": json.dumps({"phone": USER_PHONE}),
        }

        sanitized_request = TransactionProducerCreateRequest(**request_data)  # type: ignore

        GadgetFactory.create(type=GadgetType.PHONE, identifier=sanitized_request.recipient.phone)  # type: ignore

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        assert transaction.buyer_id == user.id

        mock_invite_sms.assert_not_called()

    def test_no_location_type(
        self,
        client: APIClient,
        geo_json_file: BufferedReader,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "latitude": 0,
            "longitude": 0,
            "location_file": geo_json_file,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_qr_file_invalid_syntax(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        bad_file = io.BytesIO(b"not-json")

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": TransactionLocation.QR,
            "location_file": bad_file.read(),
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="multipart")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_farm_latitude_without_longitude(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "farm_latitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_farm_longitude_without_latitude(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "farm_longitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_invalid_latitude_boundary(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": 91,  # Invalid latitude
            "transaction_longitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_invalid_longitude_boundary(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": 0,
            "transaction_longitude": 181,  # Invalid longitude
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_recipient_invalid_multiple_fields(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "recipient": json.dumps({"email": "test@example.com", "phone": "1234567890"}),
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_latitude_boundary_minus_90(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": -90,  # Valid boundary
            "transaction_longitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

    def test_latitude_boundary_90(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": 90,  # Valid boundary
            "transaction_longitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

    def test_longitude_boundary_minus_180(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": 0,
            "transaction_longitude": -180,  # Valid boundary
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

    def test_longitude_boundary_180(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "transaction_latitude": 0,
            "transaction_longitude": 180,  # Valid boundary
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

    def test_recipient_not_implemented_error(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        # This will trigger the NotImplementedError in the recipient validator
        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "recipient": 123,  # Invalid type that's not None or str
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR, response_json
        assert response_json == snapshot

    def test_latitude_without_longitude(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": TransactionLocation.MANUAL,
            "transaction_latitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_longitude_without_latitude(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": TransactionLocation.MANUAL,
            "transaction_longitude": 0,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_commodity_does_not_exist(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)
        user = UserFactory.create()
        request_data = {
            "commodity_id": "12345678-1234-1234-1234-123456789012",
            "volume": 1,
            "is_buying_from_farmer": True,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_unauthorized(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_forbidden(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(with_gadgets=False)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.FORBIDDEN, response_json
        assert response_json == snapshot

    def test_user_deleted(self, client: APIClient, snapshot: SnapshotAssertion) -> None:
        # Arrange
        user = UserFactory.create(is_deleted=True)
        client.login(user)

        # Act
        response = client.get(path=self.URL)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.UNAUTHORIZED, response_json
        assert response_json == snapshot

    def test_location_file_missing_for_qr(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "location": TransactionLocation.QR,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_location_file_missing_for_file(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "location": TransactionLocation.FILE,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_location_file_invalid_json(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        invalid_json_file = io.BytesIO(b'{"invalid": "json"')
        invalid_json_file.name = "invalid.json"

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "location": TransactionLocation.QR,
            "location_file": invalid_json_file,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_location_file_invalid_geojson(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        invalid_geojson_file = io.BytesIO(b'{"valid": "json", "but": "not_geojson"}')
        invalid_geojson_file.name = "invalid_geojson.json"

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "is_buying_from_farmer": True,
            "location": TransactionLocation.QR,
            "location_file": invalid_geojson_file,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot
