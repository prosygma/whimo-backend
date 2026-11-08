import json
from copy import deepcopy
from dataclasses import dataclass

from django.core.cache import cache
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import DatabaseError

from whimo.camertrace.models import DEFAULT_TRACEABILITY, GeodataOptions, GeodataSource, TraceabilityRule
from whimo.db.enums.transactions import TransactionLocation, TransactionTraceability

OPTIONS_CACHE_KEY = "camertrace:geodata_options"
RULES_CACHE_KEY = "camertrace:traceability_rules"
CACHE_TIMEOUT = 60 * 60

QR_SOURCE_CICC = "cicc"
# Keys a CICC plot QR code must carry; the apps copy them into the GeoJSON feature properties.
CICC_REQUIRED_PROPERTIES = ("NIPr_CICC", "GLN_Parcelle", "Lien_GS1_Parcelle")
CICC_SOURCE_MARK = "CICC"
MIN_POLYGON_POINTS = 4  # 3 corners plus the closing point


@dataclass(frozen=True)
class Options:
    ask_on_plot: bool = True
    allow_gps_point: bool = True
    allow_cicc_qr: bool = False


def get_options() -> Options:
    options: Options | None = cache.get(OPTIONS_CACHE_KEY)
    if options is None:
        try:
            row = GeodataOptions.load()
        except DatabaseError:
            return Options()
        options = Options(
            ask_on_plot=row.ask_on_plot,
            allow_gps_point=row.allow_gps_point,
            allow_cicc_qr=row.allow_cicc_qr,
        )
        cache.set(OPTIONS_CACHE_KEY, options, CACHE_TIMEOUT)
    return options


def get_rules() -> dict[str, str]:
    rules: dict[str, str] | None = cache.get(RULES_CACHE_KEY)
    if rules is None:
        try:
            rules = dict(TraceabilityRule.objects.values_list("source", "traceability"))
        except DatabaseError:
            return {}
        cache.set(RULES_CACHE_KEY, rules, CACHE_TIMEOUT)
    return rules


def clear_cache() -> None:
    cache.delete_many([OPTIONS_CACHE_KEY, RULES_CACHE_KEY])


def geodata_source(
    location: TransactionLocation | None, qr_source: str | None, is_buying_from_farmer: bool
) -> GeodataSource:
    if location == TransactionLocation.QR and qr_source == QR_SOURCE_CICC:
        return GeodataSource.CICC_QR
    if location is not None:
        return GeodataSource(location.value)
    return GeodataSource.NONE_FROM_FARMER if is_buying_from_farmer else GeodataSource.NONE


def producer_traceability(source: GeodataSource) -> TransactionTraceability:
    value = get_rules().get(source.value)
    if value is None:
        return DEFAULT_TRACEABILITY[source]
    return TransactionTraceability(value)


def is_cicc_geojson(location_file: InMemoryUploadedFile, *, require_source_mark: bool = False) -> bool:
    """True when the (already normalised) GeoJSON is a CICC plot: one polygon of at least 3
    corners, whose feature carries every CICC key (their values are not checked yet).
    With `require_source_mark`, the feature must also say `"Source": "CICC"`, as the apps write it."""
    try:
        data = json.loads(deepcopy(location_file).read().decode())
        features = data["features"] if data.get("type") == "FeatureCollection" else [data]
        if len(features) != 1:
            return False
        feature = features[0]
        properties = feature.get("properties") or {}
        geometry = feature["geometry"]
        ring = geometry["coordinates"][0]
    except (ValueError, KeyError, TypeError, IndexError, AttributeError):
        return False
    if require_source_mark and properties.get("Source") != CICC_SOURCE_MARK:
        return False
    return (
        geometry.get("type") == "Polygon"
        and len(ring) >= MIN_POLYGON_POINTS
        and all(key in properties for key in CICC_REQUIRED_PROPERTIES)
    )
