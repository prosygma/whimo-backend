from http import HTTPStatus

import pytest
from django.urls import reverse

from tests.helpers.clients import APIClient
from whimo.languages import services
from whimo.languages.models import Language

pytestmark = [pytest.mark.django_db]


class TestLanguagesList:
    URL = reverse("languages_list")

    def test_lists_enabled_languages_in_order(self, client: APIClient) -> None:
        # Arrange
        Language.objects.filter(code="es").update(is_enabled=False)
        services.clear_cache()  # update() sends no signal
        Language.objects.create(code="hi", name="हिन्दी", english_name="Hindi", flag="🇮🇳", position=0)

        # Act
        response = client.get(self.URL)

        # Assert
        assert response.status_code == HTTPStatus.OK, response.data
        assert response.data["data"]["default"] == "en"
        assert [language["code"] for language in response.data["data"]["languages"]] == ["hi", "en", "fr"]
        assert response.data["data"]["languages"][0] == {
            "code": "hi",
            "name": "हिन्दी",
            "english_name": "Hindi",
            "flag": "🇮🇳",
            "version": 1,
        }
        assert "public" in response["Cache-Control"]

    def test_ignores_an_invalid_token(self, client: APIClient) -> None:
        client.credentials(HTTP_AUTHORIZATION="Bearer expired")

        response = client.get(self.URL)

        assert response.status_code == HTTPStatus.OK

    def test_follows_default_changes(self, client: APIClient) -> None:
        client.get(self.URL)  # fills the cache
        fr = Language.objects.get(code="fr")
        fr.is_default = True
        fr.save()

        response = client.get(self.URL)

        assert response.data["data"]["default"] == "fr"
        assert Language.objects.filter(is_default=True).count() == 1


class TestLanguageStrings:
    def url(self, code: str, platform: str) -> str:
        return reverse("languages_strings", args=(code, platform))

    def test_returns_uploaded_strings_of_a_platform(self, client: APIClient) -> None:
        Language.objects.create(
            code="hi",
            name="हिन्दी",
            translations={"web": {"common": {"email": "ईमेल"}}, "android": {"email": "ईमेल"}},
            version=3,
        )

        response = client.get(self.url("hi", "web"))

        assert response.status_code == HTTPStatus.OK, response.data
        assert response.data["data"] == {"code": "hi", "version": 3, "strings": {"common": {"email": "ईमेल"}}}
        assert response["ETag"] == '"hi-3"'

    def test_shipped_language_without_uploads_is_empty(self, client: APIClient) -> None:
        response = client.get(self.url("fr", "ios"))

        assert response.status_code == HTTPStatus.OK
        assert response.data["data"]["strings"] == {}

    @pytest.mark.parametrize(("code", "platform"), [("fr", "desktop"), ("de", "web"), ("es", "web")])
    def test_not_found(self, client: APIClient, code: str, platform: str) -> None:
        Language.objects.filter(code="es").update(is_enabled=False)
        services.clear_cache()  # update() sends no signal

        response = client.get(self.url(code, platform))

        assert response.status_code == HTTPStatus.NOT_FOUND
