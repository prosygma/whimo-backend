import json
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.core.files.uploadedfile import InMemoryUploadedFile
from pydantic import field_validator, model_validator

from whimo.common.schemas.base import BaseRequest, PaginationRequest
from whimo.common.schemas.dto import CreateGadgetDTO
from whimo.db.enums import TransactionAction, TransactionLocation, TransactionStatus
from whimo.transactions.schemas.dto import FeatureCollection
from whimo.transactions.schemas.errors import (
    CommodityGroupRequiredError,
    InvalidLatitudeError,
    InvalidLongitudeError,
    InvalidStatusUpdateError,
    LocationFileInvalidSyntaxError,
    LocationFileMustBeProvidedError,
    LocationFileNotSupportedError,
    OnlyAcceptedStatusAllowedError,
    PartialLocationError,
    RecipientInvalidError,
)


def validate_latitude(latitude: Decimal | None) -> Decimal | None:
    if latitude is None:
        return None
    if not (-90 <= Decimal(latitude) <= 90):  # noqa: PLR2004 Magic value used in comparison
        raise InvalidLatitudeError
    return latitude


def validate_longitude(longitude: Decimal | None) -> Decimal | None:
    if longitude is None:
        return None
    if not (-180 <= Decimal(longitude) <= 180):  # noqa: PLR2004 Magic value used in comparison
        raise InvalidLongitudeError
    return longitude


class RecipientRequest(BaseRequest, CreateGadgetDTO):
    name: str | None = None

    @model_validator(mode="after")
    def validate_recipient(self) -> "RecipientRequest":
        fields = self.model_dump(exclude_none=True)
        if len(fields) > 1:
            raise RecipientInvalidError

        return self


class BaseTransactionRequest(BaseRequest):
    commodity_id: UUID
    volume: Decimal
    recipient: RecipientRequest | None = None

    transaction_latitude: Decimal | None = None
    transaction_longitude: Decimal | None = None

    @field_validator("transaction_latitude", mode="before")
    def validate_transaction_latitude(cls, latitude: Decimal | None) -> Decimal | None:
        return validate_latitude(latitude)

    @field_validator("transaction_longitude", mode="before")
    def validate_transaction_longitude(cls, longitude: Decimal | None) -> Decimal | None:
        return validate_longitude(longitude)

    @field_validator("recipient", mode="before")
    def validate_recipient(cls, value: Any | None) -> RecipientRequest | None:
        if value is None:
            return None

        if isinstance(value, str):
            return RecipientRequest(**json.loads(value))

        raise NotImplementedError

    @model_validator(mode="after")
    def validate_transaction_location(self) -> "BaseTransactionRequest":
        if self.transaction_latitude is None and self.transaction_longitude is not None:
            raise PartialLocationError

        if self.transaction_latitude is not None and self.transaction_longitude is None:
            raise PartialLocationError

        return self


class TransactionProducerCreateRequest(BaseTransactionRequest):
    is_buying_from_farmer: bool

    farm_latitude: Decimal | None = None
    farm_longitude: Decimal | None = None

    location_file: InMemoryUploadedFile | None = None

    location: TransactionLocation | None = None

    @field_validator("farm_latitude", mode="before")
    def validate_farm_latitude(cls, latitude: Decimal | None) -> Decimal | None:
        return validate_latitude(latitude)

    @field_validator("farm_longitude", mode="before")
    def validate_farm_longitude(cls, longitude: Decimal | None) -> Decimal | None:
        return validate_longitude(longitude)

    @model_validator(mode="after")  # type: ignore
    def validate_farm_location(self) -> "BaseTransactionRequest":
        if self.farm_latitude is None and self.farm_longitude is not None:
            raise PartialLocationError

        if self.farm_latitude is not None and self.farm_longitude is None:
            raise PartialLocationError

        return self

    @model_validator(mode="after")  # type: ignore
    def validate_location_file(self) -> "BaseTransactionRequest":
        if self.location in {None, TransactionLocation.MANUAL, TransactionLocation.GPS} and self.location_file:
            raise LocationFileNotSupportedError

        if self.location in {TransactionLocation.FILE, TransactionLocation.QR} and not self.location_file:
            raise LocationFileMustBeProvidedError

        if self.location_file and self.location == TransactionLocation.QR:
            try:
                location_content = deepcopy(self.location_file).read().decode()
                location_data = json.loads(location_content)
                FeatureCollection.model_validate(location_data)
            except Exception as err:
                raise LocationFileInvalidSyntaxError from err

        return self


class TransactionDownstreamCreateRequest(BaseTransactionRequest):
    action: TransactionAction


class TransactionStatusUpdateRequest(BaseRequest):
    status: TransactionStatus

    @field_validator("status", mode="before")
    def validate_status(cls, value: TransactionStatus) -> TransactionStatus:
        if value not in {TransactionStatus.ACCEPTED, TransactionStatus.REJECTED}:
            raise InvalidStatusUpdateError
        return value


class TransactionListRequest(PaginationRequest):
    search: str | None = None
    status: TransactionStatus | None = None
    action: TransactionAction | None = None
    created_at_from: datetime | None = None
    created_at_to: datetime | None = None
    commodity_group_id: UUID | None = None
    buyer_id: UUID | None = None

    @model_validator(mode="after")
    def validate_buyer(self) -> "TransactionListRequest":
        if self.buyer_id:
            if not self.commodity_group_id:
                raise CommodityGroupRequiredError

            if self.status != TransactionStatus.ACCEPTED:
                raise OnlyAcceptedStatusAllowedError

        return self


class TransactionGeodataUpdateRequest(BaseRequest):
    location: TransactionLocation
    location_file: InMemoryUploadedFile

    @model_validator(mode="after")
    def validate_location_file(self) -> "TransactionGeodataUpdateRequest":
        if self.location not in {TransactionLocation.FILE, TransactionLocation.QR}:
            raise LocationFileNotSupportedError

        return self
