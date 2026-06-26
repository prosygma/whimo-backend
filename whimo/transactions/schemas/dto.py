from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from whimo.commodities.schemas.dto import CommodityWithGroupDTO
from whimo.common.schemas.dto import BaseModelDTO
from whimo.db.enums import TransactionAction, TransactionLocation, TransactionStatus, TransactionType
from whimo.db.enums.transactions import TransactionTraceability
from whimo.users.schemas.dto import UserDTO

FloatDecimal = Annotated[Decimal, PlainSerializer(lambda x: float(x), return_type=float, when_used="json")]


class TransactionDTO(BaseModelDTO):
    created_at: datetime | None

    type: TransactionType
    status: TransactionStatus
    action: TransactionAction | None
    traceability: TransactionTraceability | None

    location: TransactionLocation | None

    transaction_latitude: FloatDecimal | None
    transaction_longitude: FloatDecimal | None

    farm_latitude: FloatDecimal | None
    farm_longitude: FloatDecimal | None

    commodity: CommodityWithGroupDTO
    volume: FloatDecimal

    is_buying_from_farmer: bool
    is_automatic: bool
    expires_at: datetime | None
    updated_at: datetime

    seller: UserDTO | None
    buyer: UserDTO | None
    created_by_id: UUID


class TraceabilityCountsDTO(BaseModel):
    counts: dict[TransactionTraceability, int]


class FeatureProperties(BaseModel):
    model_config = ConfigDict(extra="allow")

    producer_name: str | None = Field(alias="ProducerName", default=None)
    producer_country: str | None = Field(alias="ProducerCountry", default=None)
    production_place: str | None = Field(alias="ProductionPlace", default=None)
    transaction_id: str | None = Field(alias="TransactionId", default=None)


class PolygonGeometry(BaseModel):
    type: Literal["Polygon"] = "Polygon"
    coordinates: list[list[list[FloatDecimal]]]


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: list[FloatDecimal]


FeatureGeometry = Annotated[PolygonGeometry | PointGeometry, Field(discriminator="type")]


class Feature(BaseModel):
    type: str = "Feature"
    properties: FeatureProperties
    geometry: FeatureGeometry


class FeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[Feature]

    @classmethod
    def from_geojson(cls, data: dict[str, Any]) -> "FeatureCollection":
        match data:
            case {"type": "Feature"}:
                return cls(features=[Feature.model_validate(data)])
            case _:
                return cls.model_validate(data)


class ChainFeatureCollectionDTO(BaseModel):
    feature_collection: FeatureCollection
    succeed_transactions: list[UUID]
    failed_transactions: list[UUID]


class ChainLocationBundleDTO(BaseModel):
    geojson_merged_transactions: list[UUID]
    custom_location_file_transactions: list[UUID]
    no_location_file_transactions: list[UUID]


class ConversionDTO(BaseModelDTO):
    commodity: CommodityWithGroupDTO
    quantity: FloatDecimal


class ConversionRecipeDTO(BaseModelDTO):
    name: str
    inputs: list[ConversionDTO]
    outputs: list[ConversionDTO]
