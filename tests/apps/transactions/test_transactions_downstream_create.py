import json
from datetime import timedelta
from http import HTTPStatus
from io import BufferedReader
from unittest.mock import MagicMock, Mock
from uuid import UUID

import pytest
from django.conf import settings
from django.urls import reverse
from freezegun.api import FrozenDateTimeFactory
from pytest_mock import MockerFixture
from syrupy import SnapshotAssertion
from syrupy.filters import props

from tests.factories.commodities import CommodityFactory
from tests.factories.users import GadgetFactory, UserFactory
from tests.helpers.clients import APIClient
from tests.helpers.constants import DEFAULT_DATETIME, USER_EMAIL, USER_PHONE
from whimo.auth.registration.services import RegistrationService
from whimo.db.enums import GadgetType, TransactionAction, TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.notifications import NotificationStatus, NotificationType
from whimo.db.models import Gadget, Notification, Transaction
from whimo.transactions.schemas.requests import TransactionDownstreamCreateRequest

pytestmark = [pytest.mark.django_db]


class TestTransactionsDownstreamCreate:
    URL = reverse("transactions_downstream_create")

    @pytest.mark.parametrize("location", TransactionLocation)
    @pytest.mark.parametrize("action", TransactionAction)
    def test_success(  # noqa: PLR0913 Too many arguments in function definition
        self,
        location: TransactionLocation,
        action: TransactionAction,
        geo_json_file: BufferedReader,
        mock_default_storage: MagicMock,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipient = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "location": location,
            "transaction_latitude": 0,
            "transaction_longitude": 0,
            "action": action,
            "recipient": json.dumps({"name": recipient.username}),
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

        assert transaction.type == TransactionType.DOWNSTREAM
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.traceability is None

        assert transaction.commodity_id == UUID(request_data["commodity_id"])  # type: ignore
        assert transaction.volume == request_data["volume"]

        assert transaction.location is None
        assert transaction.transaction_latitude == request_data["transaction_latitude"]
        assert transaction.transaction_longitude == request_data["transaction_longitude"]

        assert not transaction.is_buying_from_farmer
        assert not transaction.is_automatic
        assert transaction.expires_at == DEFAULT_DATETIME + timedelta(days=settings.WHIMO_TRANSACTION_EXPIRATION_DAYS)

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id == recipient.id
        elif action == TransactionAction.SELLING:
            assert transaction.buyer_id == recipient.id
            assert transaction.seller_id == user.id

        assert transaction.created_by_id == user.id

        notification = Notification.objects.get()

        assert notification.type == NotificationType.TRANSACTION_PENDING
        assert notification.status == NotificationStatus.PENDING
        assert notification.data["transaction"]["id"] == str(transaction.pk)  # type: ignore
        assert notification.received_by_id == recipient.id
        assert notification.created_by_id == user.id

    @pytest.mark.parametrize("action", TransactionAction)
    def test_no_location(
        self,
        client: APIClient,
        action: TransactionAction,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipient = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "action": action,
            "recipient": json.dumps({"name": recipient.username}),
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

    @pytest.mark.parametrize("action", TransactionAction)
    def test_no_recipient(
        self,
        client: APIClient,
        action: TransactionAction,
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
            "action": action,
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id is None
        elif action == TransactionAction.SELLING:
            assert transaction.buyer_id is None
            assert transaction.seller_id == user.id

    @pytest.mark.parametrize("action", TransactionAction)
    def test_create_recipient_and_send_invite_email(  # noqa: PLR0913 Too many arguments in function definition
        self,
        client: APIClient,
        action: TransactionAction,
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
            "action": action,
            "recipient": json.dumps({"email": USER_EMAIL}),
        }
        sanitized_request = TransactionDownstreamCreateRequest(**request_data)  # type: ignore

        mock_create_username.return_value = "John Doe"

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        recipient_email = Gadget.objects.get(type=GadgetType.EMAIL, identifier=sanitized_request.recipient.email)  # type: ignore

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id == recipient_email.user_id
        elif action == TransactionAction.SELLING:
            assert transaction.seller_id == user.id
            assert transaction.buyer_id == recipient_email.user_id

        # Verify invite email was sent to newly created recipient
        mock_invite_email.assert_called_once_with(
            recipients=[USER_EMAIL],
            subject="Welcome to WHIMO!",
            message="You have been invited to Whimo!",
        )

    @pytest.mark.parametrize("action", TransactionAction)
    def test_find_recipient_with_email(
        self,
        client: APIClient,
        action: TransactionAction,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
        mock_invite_email: MagicMock,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "action": action,
            "recipient": json.dumps({"email": USER_EMAIL}),
        }
        sanitized_request = TransactionDownstreamCreateRequest(**request_data)  # type: ignore
        recipient_gadget = GadgetFactory.create(type=GadgetType.EMAIL, identifier=sanitized_request.recipient.email)  # type: ignore

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id == recipient_gadget.user_id
        elif action == TransactionAction.SELLING:
            assert transaction.seller_id == user.id
            assert transaction.buyer_id == recipient_gadget.user_id

        # Verify no invite email was sent for existing recipient
        mock_invite_email.assert_not_called()

    @pytest.mark.parametrize("action", TransactionAction)
    def test_create_recipient_and_send_invite_phone(  # noqa: PLR0913 Too many arguments in function definition
        self,
        client: APIClient,
        action: TransactionAction,
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
            "action": action,
            "recipient": json.dumps({"phone": USER_PHONE}),
        }
        sanitized_request = TransactionDownstreamCreateRequest(**request_data)  # type: ignore

        mock_create_username.return_value = "John Doe"

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        recipient_phone = Gadget.objects.get(type=GadgetType.PHONE, identifier=sanitized_request.recipient.phone)  # type: ignore

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id == recipient_phone.user_id
        elif action == TransactionAction.SELLING:
            assert transaction.seller_id == user.id
            assert transaction.buyer_id == recipient_phone.user_id

        mock_invite_sms.assert_called_once_with(
            recipient=USER_PHONE.lstrip("+"),
            message="You have been invited to Whimo!",
        )

    @pytest.mark.parametrize("action", TransactionAction)
    def test_find_recipient_with_phone(
        self,
        client: APIClient,
        action: TransactionAction,
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
            "action": action,
            "recipient": json.dumps({"phone": USER_PHONE}),
        }
        sanitized_request = TransactionDownstreamCreateRequest(**request_data)  # type: ignore
        recipient_gadget = GadgetFactory.create(type=GadgetType.PHONE, identifier=sanitized_request.recipient.phone)  # type: ignore

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_json
        assert response_json == snapshot(exclude=props("id"))

        transaction = Transaction.objects.get(pk=response_json["data"]["id"])

        if action == TransactionAction.BUYING:
            assert transaction.buyer_id == user.id
            assert transaction.seller_id == recipient_gadget.user_id
        elif action == TransactionAction.SELLING:
            assert transaction.seller_id == user.id
            assert transaction.buyer_id == recipient_gadget.user_id

        # Verify no invite SMS was sent for existing recipient
        mock_invite_sms.assert_not_called()

    def test_latitude_without_longitude(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        recipient = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"name": recipient.username}),
            "location": TransactionLocation.MANUAL,
            "transaction_latitude": 0,
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
        recipient = UserFactory.create()
        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 1,
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"name": recipient.username}),
            "location": TransactionLocation.MANUAL,
            "transaction_longitude": 0,
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
        recipient = UserFactory.create()

        request_data = {
            "commodity_id": "12345678-1234-1234-1234-123456789012",
            "volume": 1,
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"name": recipient.username}),
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_recipient_does_not_exist(
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
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"name": "Not Existing Recipient"}),
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND, response_json
        assert response_json == snapshot

    def test_recipient_name_with_data(
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
            "action": TransactionAction.BUYING,
            "recipient": json.dumps(
                {
                    "name": user.username,
                    "email": USER_EMAIL,
                    "phone": USER_PHONE,
                }
            ),
        }
        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST, response_json
        assert response_json == snapshot

    def test_recipient_same_as_user(
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
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"name": user.username}),
        }

        client.login(user)

        # Act
        response = client.post(path=self.URL, data=request_data)
        response_json = response.json()

        # Assert
        assert response.status_code == HTTPStatus.CONFLICT, response_json
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

    def test_recipient_existing_user(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        existing_user = UserFactory.create()

        gadget = GadgetFactory.create(user=existing_user, identifier="test@example.com")

        client.login(user)

        commodity = CommodityFactory.create()

        request_data = {
            "commodity_id": commodity.id,
            "volume": 100.0,
            "recipient": json.dumps({"email": gadget.identifier}),
        }

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_recipient_new_user(
        self,
        client: APIClient,
        mocker: MockerFixture,
        freezer: FrozenDateTimeFactory,
        snapshot: SnapshotAssertion,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()

        mock_register = mocker.patch.object(RegistrationService, "register")
        mock_register.return_value = UserFactory.create()

        commodity = CommodityFactory.create()

        client.login(user)

        request_data = {
            "commodity_id": str(commodity.id),
            "volume": 100.0,
            "location": TransactionLocation.MANUAL,
            "transaction_latitude": 0,
            "transaction_longitude": 0,
            "action": TransactionAction.BUYING,
            "recipient": json.dumps({"email": "newuser@example.com"}),
        }

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.OK, snapshot
        mock_register.assert_called_once()

    def test_recipient_none(
        self,
        client: APIClient,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()

        commodity = CommodityFactory.create()

        client.login(user)

        request_data = {"commodity_id": commodity.id, "volume": 100.0}

        # Act
        response = client.post(path=self.URL, data=request_data, format="json")

        # Assert
        assert response.status_code == HTTPStatus.BAD_REQUEST
