from decimal import Decimal
from io import BytesIO
from uuid import UUID

import pytest
from django.core.files.uploadedfile import InMemoryUploadedFile
from pydantic import ValidationError

from whimo.db.enums.transactions import TransactionLocation
from whimo.transactions.schemas.errors import (
    InvalidLatitudeError,
    InvalidLongitudeError,
    PartialLocationError,
    RecipientInvalidError,
)
from whimo.transactions.schemas.requests import (
    BaseTransactionRequest,
    RecipientRequest,
    TransactionGeodataUpdateRequest,
    validate_latitude,
    validate_longitude,
)

pytestmark = [pytest.mark.django_db]


class TestSchemasValidators:
    def test_validate_latitude_none(self) -> None:
        # Arrange & Act
        result = validate_latitude(None)

        # Assert
        assert result is None

    def test_validate_longitude_none(self) -> None:
        # Arrange & Act
        result = validate_longitude(None)

        # Assert
        assert result is None

    def test_validate_latitude_invalid(self) -> None:
        with pytest.raises(InvalidLatitudeError):
            validate_latitude(Decimal("91"))

    def test_validate_longitude_invalid(self) -> None:
        with pytest.raises(InvalidLongitudeError):
            validate_longitude(Decimal("181"))

    def test_base_transaction_request_recipient_none(self) -> None:
        # Arrange
        class TestRequest(BaseTransactionRequest):
            pass

        # Act
        request = TestRequest(
            commodity_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            volume=Decimal("10.5"),
            recipient=None,
        )

        # Assert
        assert request.recipient is None

    def test_base_transaction_request_partial_location_error_latitude_only(self) -> None:
        # Arrange
        class TestRequest(BaseTransactionRequest):
            pass

        # Act & Assert
        with pytest.raises(PartialLocationError):
            TestRequest(
                commodity_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                volume=Decimal("10.5"),
                transaction_latitude=Decimal("45.0"),
                transaction_longitude=None,
            )

    def test_base_transaction_request_partial_location_error_longitude_only(self) -> None:
        # Arrange
        class TestRequest(BaseTransactionRequest):
            pass

        # Act & Assert
        with pytest.raises(PartialLocationError):
            TestRequest(
                commodity_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
                volume=Decimal("10.5"),
                transaction_latitude=None,
                transaction_longitude=Decimal("90.0"),
            )

    def test_transaction_geodata_update_request_location_file_required_file(self) -> None:
        # Act & Assert
        with pytest.raises(ValidationError):
            TransactionGeodataUpdateRequest.model_validate(
                {"location": TransactionLocation.FILE, "location_file": None}
            )

    def test_transaction_geodata_update_request_location_file_required_qr(self) -> None:
        # Act & Assert
        with pytest.raises(ValidationError):
            TransactionGeodataUpdateRequest.model_validate({"location": TransactionLocation.QR, "location_file": None})

    def test_transaction_geodata_update_request_invalid_json(self) -> None:
        # Arrange
        invalid_json_content = b'{"invalid": "json"'
        mock_file = InMemoryUploadedFile(
            BytesIO(invalid_json_content), None, "test.json", "application/json", len(invalid_json_content), None
        )

        # Act
        request = TransactionGeodataUpdateRequest(location=TransactionLocation.QR, location_file=mock_file)

        # Assert
        assert request.location == TransactionLocation.QR
        assert request.location_file == mock_file

    def test_transaction_geodata_update_request_invalid_geojson(self) -> None:
        # Arrange
        invalid_geojson_content = b'{"valid": "json", "but": "not_geojson"}'
        mock_file = InMemoryUploadedFile(
            BytesIO(invalid_geojson_content), None, "test.json", "application/json", len(invalid_geojson_content), None
        )

        # Act
        request = TransactionGeodataUpdateRequest(location=TransactionLocation.QR, location_file=mock_file)

        # Assert
        assert request.location == TransactionLocation.QR
        assert request.location_file == mock_file

    def test_recipient_request_invalid_multiple_fields(self) -> None:
        with pytest.raises(RecipientInvalidError):
            RecipientRequest(name="Test User", email="test@example.com", phone="1234567890")
