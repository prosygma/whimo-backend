import csv
import json
from io import BytesIO
from pathlib import Path

import pytest
import zxingcpp
from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook
from PIL import Image

from whimo.transactions.qr_cards import FarmRow, build_cards, render_cards_pdf, render_qr

pytestmark = [pytest.mark.django_db]

FARM = ("F-001", "-6.204000", "35.102000")


def rows(*values: tuple[str, str, str]) -> list[FarmRow]:
    return [
        FarmRow(number=number, farmer_id=farmer_id, latitude=latitude, longitude=longitude)
        for number, (farmer_id, latitude, longitude) in enumerate(values, start=2)
    ]


class TestBuildCards:
    def test_a_farm_becomes_one_payload(self) -> None:
        # Act
        cards, rejected = build_cards(rows(FARM))

        # Assert
        assert not rejected
        assert [card.farmer_id for card in cards] == ["F-001"]
        assert cards[0].payload == (
            '{"type":"Feature","properties":{"farmer_id":"F-001"},'
            '"geometry":{"type":"Point","coordinates":[35.102,-6.204]}}'
        )

    def test_coordinates_are_rounded_to_six_decimals(self) -> None:
        # Act
        cards, _ = build_cards(rows(("F-001", "-6.2040006", "35.1029999")))

        # Assert
        assert json.loads(cards[0].payload)["geometry"]["coordinates"] == [35.103, -6.204001]

    @pytest.mark.parametrize(
        ("farm", "reason"),
        [
            (("", "-6.204", "35.102"), "farmer id is empty"),
            (("F-001", "", "35.102"), "coordinates are not numbers"),
            (("F-001", "north", "35.102"), "coordinates are not numbers"),
            (("F-001", "35.102", "-6.204"), "coordinates look swapped"),
            (("F-001", "48.85", "2.35"), "coordinates are outside the bounding box"),
        ],
    )
    def test_a_bad_row_is_rejected_with_its_reason(self, farm: tuple[str, str, str], reason: str) -> None:
        # Act
        cards, rejected = build_cards(rows(farm))

        # Assert
        assert not cards
        assert [(item.number, item.reason) for item in rejected] == [(2, reason)]

    def test_a_swapped_pair_is_never_corrected(self) -> None:
        # Act
        cards, rejected = build_cards(rows(("F-001", "35.102", "-6.204")))

        # Assert
        assert not cards
        assert rejected[0].reason == "coordinates look swapped"

    def test_duplicates_are_rejected_and_the_first_row_stays(self) -> None:
        # Act
        cards, rejected = build_cards(
            rows(
                FARM,
                ("F-001", "-6.300000", "35.200000"),
                ("F-002", "-6.204000", "35.102000"),
            ),
        )

        # Assert
        assert [card.farmer_id for card in cards] == ["F-001"]
        assert [(item.number, item.reason) for item in rejected] == [
            (3, "duplicate farmer id"),
            (4, "same coordinates as F-001"),
        ]


class TestRenderQr:
    def test_a_generated_code_decodes_back_to_its_payload(self) -> None:
        # Arrange
        cards, _ = build_cards(rows(FARM))
        payload = cards[0].payload

        # Act
        image = Image.open(BytesIO(render_qr(payload)))
        decoded = zxingcpp.read_barcode(image)

        # Assert
        assert decoded is not None
        assert decoded.text == payload
        assert decoded.format == zxingcpp.BarcodeFormat.QRCode

    def test_cards_fill_the_pages_of_the_pdf(self, tmp_path: Path) -> None:
        # Arrange
        farms = [(f"F-{number:03}", "-6.204000", f"35.{number:06}") for number in range(1, 26)]
        cards, rejected = build_cards(rows(*farms))
        assert not rejected

        output = tmp_path / "cards.pdf"

        # Act
        pages = render_cards_pdf(cards, output, columns=3, rows=4)

        # Assert
        assert pages == 3  # noqa: PLR2004 Magic value used in comparison
        assert output.read_bytes().startswith(b"%PDF")


class TestGenerateFarmQrCardsCommand:
    def spreadsheet(self, path: Path, farms: list[tuple[str, str, str]]) -> Path:
        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.append(["Farmer ID", "Latitude", "Longitude"])
        for farm in farms:
            sheet.append(list(farm))
        workbook.save(path)
        return path

    def test_it_writes_the_cards_and_the_rejects(self, tmp_path: Path) -> None:
        # Arrange
        source = self.spreadsheet(
            tmp_path / "farms.xlsx",
            [FARM, ("F-002", "48.85", "2.35"), ("F-003", "-6.300000", "35.200000")],
        )
        output = tmp_path / "cards.pdf"
        rejects = tmp_path / "rejects.csv"

        # Act
        call_command("generate_farm_qr_cards", str(source), str(output), "--rejects", str(rejects))

        # Assert
        assert output.read_bytes().startswith(b"%PDF")

        with rejects.open() as rejects_file:
            reported = list(csv.reader(rejects_file))

        assert reported == [
            ["Row", "Farmer ID", "Reason"],
            ["3", "F-002", "coordinates are outside the bounding box"],
        ]

    def test_a_missing_column_stops_the_run(self, tmp_path: Path) -> None:
        # Arrange
        source = self.spreadsheet(tmp_path / "farms.xlsx", [FARM])

        # Act / Assert
        with pytest.raises(CommandError, match="plot id"):
            call_command(
                "generate_farm_qr_cards",
                str(source),
                str(tmp_path / "cards.pdf"),
                "--id-column",
                "plot id",
            )
