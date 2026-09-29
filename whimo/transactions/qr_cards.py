import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

import segno
from pydantic import ValidationError
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from whimo.transactions.schemas.dto import FeatureCollection

# Mainland Tanzania, the bounding box the QR spec prints in its checklist.
DEFAULT_BOUNDING_BOX = (Decimal("29.3"), Decimal("-11.8"), Decimal("40.5"), Decimal("-0.9"))
COORDINATE_PRECISION = Decimal("0.000001")
PAYLOAD_SIZE_LIMIT = 1200

CARD_MARGIN = 10 * mm
CARD_PADDING = 4 * mm
LABEL_HEIGHT = 8 * mm


@dataclass(frozen=True, slots=True)
class FarmRow:
    number: int
    farmer_id: Any
    latitude: Any
    longitude: Any


@dataclass(frozen=True, slots=True)
class FarmCard:
    farmer_id: str
    payload: str


@dataclass(frozen=True, slots=True)
class RejectedRow:
    number: int
    farmer_id: str
    reason: str


def build_cards(
    rows: Iterable[FarmRow],
    bounding_box: tuple[Decimal, Decimal, Decimal, Decimal] = DEFAULT_BOUNDING_BOX,
) -> tuple[list[FarmCard], list[RejectedRow]]:
    cards: list[FarmCard] = []
    rejected: list[RejectedRow] = []
    seen_ids: set[str] = set()
    seen_points: dict[tuple[Decimal, Decimal], str] = {}

    for row in rows:
        farmer_id = str(row.farmer_id).strip() if row.farmer_id is not None else ""
        if not farmer_id:
            rejected.append(RejectedRow(row.number, farmer_id, "farmer id is empty"))
            continue

        try:
            latitude = _coordinate(row.latitude)
            longitude = _coordinate(row.longitude)
        except (InvalidOperation, TypeError, ValueError):
            rejected.append(RejectedRow(row.number, farmer_id, "coordinates are not numbers"))
            continue

        if not _inside(longitude, latitude, bounding_box):
            # Never swapped silently: a wrong pair has to be fixed in the source file.
            reason = (
                "coordinates look swapped"
                if _inside(latitude, longitude, bounding_box)
                else "coordinates are outside the bounding box"
            )
            rejected.append(RejectedRow(row.number, farmer_id, reason))
            continue

        if farmer_id in seen_ids:
            rejected.append(RejectedRow(row.number, farmer_id, "duplicate farmer id"))
            continue

        if owner := seen_points.get((latitude, longitude)):
            rejected.append(RejectedRow(row.number, farmer_id, f"same coordinates as {owner}"))
            continue

        payload = build_payload(farmer_id, latitude, longitude)
        if payload_error := _payload_error(payload):
            rejected.append(RejectedRow(row.number, farmer_id, payload_error))
            continue

        seen_ids.add(farmer_id)
        seen_points[(latitude, longitude)] = farmer_id
        cards.append(FarmCard(farmer_id=farmer_id, payload=payload))

    return cards, rejected


def build_payload(farmer_id: str, latitude: Decimal, longitude: Decimal) -> str:
    feature = {
        "type": "Feature",
        "properties": {"farmer_id": farmer_id},
        "geometry": {"type": "Point", "coordinates": [float(longitude), float(latitude)]},
    }
    return json.dumps(feature, separators=(",", ":"), ensure_ascii=False)


def render_qr(payload: str, error_level: str = "M", scale: int = 8) -> bytes:
    buffer = BytesIO()
    segno.make(payload, error=error_level).save(buffer, kind="png", scale=scale, border=4)
    return buffer.getvalue()


def render_cards_pdf(
    cards: list[FarmCard],
    output_path: Path,
    columns: int = 3,
    rows: int = 4,
    error_level: str = "M",
) -> int:
    page = canvas.Canvas(str(output_path), pagesize=A4)
    page_width, page_height = A4
    cell_width = (page_width - 2 * CARD_MARGIN) / columns
    cell_height = (page_height - 2 * CARD_MARGIN) / rows
    per_page = columns * rows

    for index, card in enumerate(cards):
        if index and index % per_page == 0:
            page.showPage()

        position = index % per_page
        left = CARD_MARGIN + (position % columns) * cell_width
        bottom = page_height - CARD_MARGIN - (position // columns + 1) * cell_height

        page.setStrokeColorRGB(0.8, 0.8, 0.8)
        page.rect(left, bottom, cell_width, cell_height)

        qr_side = min(cell_width, cell_height - LABEL_HEIGHT) - 2 * CARD_PADDING
        qr_image = ImageReader(BytesIO(render_qr(card.payload, error_level=error_level)))
        page.drawImage(
            qr_image,
            left + (cell_width - qr_side) / 2,
            bottom + LABEL_HEIGHT + CARD_PADDING,
            width=qr_side,
            height=qr_side,
        )

        page.setFillColorRGB(0, 0, 0)
        page.setFont("Helvetica", 10)
        page.drawCentredString(left + cell_width / 2, bottom + CARD_PADDING, card.farmer_id)

    page.save()
    return -(-len(cards) // per_page) if cards else 0


def _coordinate(value: Any) -> Decimal:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError("empty coordinate")
    return Decimal(str(value).strip()).quantize(COORDINATE_PRECISION)


def _inside(longitude: Decimal, latitude: Decimal, bounding_box: tuple[Decimal, ...]) -> bool:
    min_longitude, min_latitude, max_longitude, max_latitude = bounding_box
    return min_longitude <= longitude <= max_longitude and min_latitude <= latitude <= max_latitude


def _payload_error(payload: str) -> str | None:
    if len(payload.encode()) > PAYLOAD_SIZE_LIMIT:
        return f"payload over {PAYLOAD_SIZE_LIMIT} bytes"

    try:
        FeatureCollection.from_geojson(json.loads(payload))
    except (json.JSONDecodeError, ValidationError):
        return "payload is not a valid geojson feature"

    return None
