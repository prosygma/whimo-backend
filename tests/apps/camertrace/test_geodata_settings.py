from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.camertrace import services
from whimo.camertrace.models import GeodataOptions, GeodataSource, TraceabilityRule
from whimo.db.enums.transactions import TransactionLocation, TransactionTraceability

pytestmark = [pytest.mark.django_db]


class TestTraceabilityRules:
    def test_seeded_defaults(self) -> None:
        assert dict(TraceabilityRule.objects.values_list("source", "traceability")) == {
            "cicc_qr": "full",
            "qr": "conditional",
            "gps": "conditional",
            "file": "conditional",
            "manual": "partial",
            "none_from_farmer": "partial",
            "none": "incomplete",
        }

    @pytest.mark.parametrize(
        ("location", "qr_source", "from_farmer", "expected"),
        [
            (TransactionLocation.QR, "cicc", True, GeodataSource.CICC_QR),
            (TransactionLocation.QR, None, True, GeodataSource.QR),
            (TransactionLocation.GPS, "cicc", True, GeodataSource.GPS),
            (TransactionLocation.FILE, None, False, GeodataSource.FILE),
            (TransactionLocation.MANUAL, None, True, GeodataSource.MANUAL),
            (None, None, True, GeodataSource.NONE_FROM_FARMER),
            (None, None, False, GeodataSource.NONE),
        ],
    )
    def test_geodata_source(
        self, location: TransactionLocation | None, qr_source: str | None, from_farmer: bool, expected: GeodataSource
    ) -> None:
        assert services.geodata_source(location, qr_source, from_farmer) == expected

    def test_edited_rule_applies(self) -> None:
        assert services.producer_traceability(GeodataSource.GPS) == TransactionTraceability.CONDITIONAL

        rule = TraceabilityRule.objects.get(source=GeodataSource.GPS)
        rule.traceability = TransactionTraceability.FULL
        rule.save()  # the signal drops the cached rules

        assert services.producer_traceability(GeodataSource.GPS) == TransactionTraceability.FULL

    def test_missing_rule_falls_back_to_default(self) -> None:
        TraceabilityRule.objects.filter(source=GeodataSource.CICC_QR).delete()
        services.clear_cache()

        assert services.producer_traceability(GeodataSource.CICC_QR) == TransactionTraceability.FULL


class TestAppOptionsApi:
    URL = reverse("app_options")

    def test_defaults_without_login(self) -> None:
        response = Client().get(self.URL)

        assert response.status_code == HTTPStatus.OK
        data = response.json()["data"]
        assert {key: data[key] for key in ("ask_on_plot", "allow_gps_point", "allow_cicc_qr")} == {
            "ask_on_plot": True,
            "allow_gps_point": True,
            "allow_cicc_qr": False,
        }
        assert set(data["traceability_descriptions"]) == {"full", "conditional", "partial", "incomplete"}
        assert "max-age=300" in response["Cache-Control"]

    def test_follows_admin_changes(self) -> None:
        options = GeodataOptions.load()
        options.ask_on_plot = False
        options.allow_gps_point = False
        options.allow_cicc_qr = True
        options.save()

        data = Client().get(self.URL).json()["data"]
        data.pop("traceability_descriptions")

        assert data == {"ask_on_plot": False, "allow_gps_point": False, "allow_cicc_qr": True}

    def test_test_mode_route(self) -> None:
        response = Client().get("/api/v1/test/app-options/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"]["ask_on_plot"] is True


class TestTraceabilityDescriptions:
    URL = reverse("app_options")

    def descriptions(self, language: str = "en") -> dict[str, str]:
        response = Client().get(self.URL, HTTP_ACCEPT_LANGUAGE=language)
        return response.json()["data"]["traceability_descriptions"]

    def test_follow_the_seeded_rules(self) -> None:
        descriptions = self.descriptions()

        assert descriptions["full"].startswith("No geodata source gives this status")  # CICC scan is off
        assert "scanning a GeoJSON QR code" in descriptions["conditional"]
        assert "the device GPS on the plot" in descriptions["conditional"]
        assert "a point picked on the map" in descriptions["partial"]
        assert "bought from a cooperative" in descriptions["incomplete"]
        assert all("lowest status of its supplies" in text for text in descriptions.values())

    def test_enabled_cicc_scan_gives_full(self) -> None:
        options = GeodataOptions.load()
        options.allow_cicc_qr = True
        options.save()

        assert self.descriptions()["full"].startswith("Given by: scanning the CICC QR code.")

    def test_disabled_options_hide_their_source(self) -> None:
        options = GeodataOptions.load()
        options.ask_on_plot = False
        options.allow_gps_point = False
        options.save()

        text = " ".join(self.descriptions().values())
        assert "device GPS" not in text
        assert "map" not in text

    def test_edited_rule_moves_the_source(self) -> None:
        rule = TraceabilityRule.objects.get(source=GeodataSource.QR)
        rule.traceability = TransactionTraceability.FULL
        rule.save()

        descriptions = self.descriptions()
        assert "GeoJSON QR code" in descriptions["full"]
        assert "GeoJSON QR code" not in descriptions["conditional"]

    def test_no_source_left_for_incomplete(self) -> None:
        TraceabilityRule.objects.filter(source=GeodataSource.NONE).update(traceability=TransactionTraceability.PARTIAL)
        services.clear_cache()

        assert self.descriptions()["incomplete"].startswith("A chain that starts with a downstream transaction")

    def test_written_in_the_request_language(self) -> None:
        with translation.override("fr"):
            expected = translation.gettext("A downstream transaction takes the lowest status of its supplies.")

        assert expected in self.descriptions("fr")["conditional"]


class TestAdmin:
    @pytest.fixture
    def logged_admin(self, admin_client: AdminClient) -> AdminClient:
        admin_client.login(UserFactory.create(superuser=True))
        return admin_client

    def test_options_redirects_to_single_row(self, logged_admin: AdminClient) -> None:
        response = logged_admin.get(reverse("admin:camertrace_geodataoptions_changelist"))

        assert response.status_code == HTTPStatus.FOUND
        options = GeodataOptions.objects.get()
        assert str(options.pk) in response["Location"]
        assert logged_admin.get(response["Location"]).status_code == HTTPStatus.OK

    def test_rules_list(self, logged_admin: AdminClient) -> None:
        response = logged_admin.get(reverse("admin:camertrace_traceabilityrule_changelist"))

        assert response.status_code == HTTPStatus.OK
        assert "CICC QR code" in response.content.decode()

    def test_sidebar_settings_group(self, logged_admin: AdminClient) -> None:
        html = logged_admin.get(reverse("admin:index")).content.decode()

        trading, settings, whatsapp = html.find("Trading"), html.find("Settings"), html.find("WhatsApp")
        assert -1 < trading < settings < whatsapp
        assert reverse("admin:camertrace_traceabilityrule_changelist") in html
