from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

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
        assert response.json() == {
            "success": True,
            "data": {"ask_on_plot": True, "allow_gps_point": True, "allow_cicc_qr": False},
        }
        assert "max-age=300" in response["Cache-Control"]

    def test_follows_admin_changes(self) -> None:
        options = GeodataOptions.load()
        options.ask_on_plot = False
        options.allow_gps_point = False
        options.allow_cicc_qr = True
        options.save()

        data = Client().get(self.URL).json()["data"]

        assert data == {"ask_on_plot": False, "allow_gps_point": False, "allow_cicc_qr": True}

    def test_test_mode_route(self) -> None:
        response = Client().get("/api/v1/test/app-options/")

        assert response.status_code == HTTPStatus.OK
        assert response.json()["data"]["ask_on_plot"] is True


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
