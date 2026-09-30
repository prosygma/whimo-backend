import pytest
from django.urls import reverse

from tests.helpers.clients import APIClient
from whimo.languages import services
from whimo.languages.models import Language

pytestmark = [pytest.mark.django_db]

URL = reverse("system_healthcheck")


def language_of(client: APIClient, accept_language: str | None) -> str:
    headers = {"HTTP_ACCEPT_LANGUAGE": accept_language} if accept_language is not None else {}
    return client.get(URL, **headers)["Content-Language"]


class TestLanguageMiddleware:
    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("fr", "fr-fr"),
            ("fr-CA,fr;q=0.9", "fr-fr"),
            ("es-MX", "es-es"),
            ("de-DE,fr;q=0.5", "fr-fr"),
            ("de", "en-us"),
            (None, "en-us"),
        ],
    )
    def test_picks_an_enabled_language(self, client: APIClient, header: str | None, expected: str) -> None:
        assert language_of(client, header) == expected

    def test_disabled_language_falls_back_to_the_default(self, client: APIClient) -> None:
        Language.objects.filter(code="es").update(is_enabled=False)
        fr = Language.objects.get(code="fr")  # saving it below also clears the cache
        fr.is_default = True
        fr.save()

        assert language_of(client, "es") == "fr-fr"

    def test_uploaded_api_strings_translate_messages(self, client: APIClient) -> None:
        language = Language.objects.create(
            code="hi", name="हिन्दी", translations={"api": {"Service is healthy": "सेवा ठीक है"}}
        )

        response = client.get(URL, HTTP_ACCEPT_LANGUAGE="hi-IN")

        assert response["Content-Language"] == "hi"
        assert response.data["message"] == "सेवा ठीक है"

        # A new upload replaces the strings without a restart.
        language.translations = {"api": {"Service is healthy": "सब ठीक है"}}
        language.version += 1
        language.save()

        assert client.get(URL, HTTP_ACCEPT_LANGUAGE="hi")["Content-Language"] == "hi"
        assert client.get(URL, HTTP_ACCEPT_LANGUAGE="hi").data["message"] == "सब ठीक है"

    def test_without_languages_django_decides(self, client: APIClient) -> None:
        Language.objects.all().delete()
        services.clear_cache()

        assert language_of(client, "fr") == "fr-fr"


class TestDjangoCode:
    @pytest.mark.parametrize(
        ("code", "expected"), [("en", "en-US"), ("fr", "fr-FR"), ("es-es", "es-ES"), ("hi", "hi"), ("pt-br", "pt-br")]
    )
    def test_maps_to_the_settings_variant(self, code: str, expected: str) -> None:
        assert services.django_code(code) == expected
