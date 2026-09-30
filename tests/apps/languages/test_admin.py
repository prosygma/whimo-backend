import json
from http import HTTPStatus

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.languages import catalog
from whimo.languages.models import Language

pytestmark = [pytest.mark.django_db]

FIRST_UPLOAD_VERSION = 2
NEW_POSITION = 7


@pytest.fixture
def logged_admin(admin_client: AdminClient) -> AdminClient:
    admin_client.login(UserFactory.create(superuser=True))
    return admin_client


def json_file(data: dict | str, name: str = "hi.json") -> SimpleUploadedFile:
    content = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return SimpleUploadedFile(name, content.encode(), content_type="application/json")


def form_data(**overrides: object) -> dict:
    data = {
        "code": "hi",
        "name": "हिन्दी",
        "english_name": "Hindi",
        "flag": "🇮🇳",
        "is_enabled": "on",
        "position": "4",
    }
    data.update(overrides)
    return data


class TestLanguageAdmin:
    def test_changelist(self, logged_admin: AdminClient) -> None:
        response = logged_admin.get(reverse("admin:languages_language_changelist"))
        content = response.content.decode()

        assert response.status_code == HTTPStatus.OK, content
        assert "Français" in content
        assert "Download English template" in content

    def test_change(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="fr")

        response = logged_admin.get(reverse("admin:languages_language_change", args=(language.pk,)))

        assert response.status_code == HTTPStatus.OK
        assert f"/ {catalog.template_size()}" in response.content.decode()

    def test_download_template(self, logged_admin: AdminClient) -> None:
        response = logged_admin.get(reverse("admin:languages_language_download_template"))

        assert response.status_code == HTTPStatus.OK
        assert response["Content-Disposition"] == 'attachment; filename="translations-template-en.json"'
        assert json.loads(response.content) == catalog.download("en", {})

    def test_download_translations(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="fr")
        language.translations = {"android": {"email": "Courriel"}}
        language.save()

        response = logged_admin.get(reverse("admin:languages_language_download_translations", args=(language.pk,)))

        assert response.status_code == HTTPStatus.OK
        assert json.loads(response.content)["android"]["email"] == "Courriel"

    def test_add_language_with_translations(self, logged_admin: AdminClient) -> None:
        # Arrange: the English template with two strings translated
        upload = catalog.download("en", {})
        upload["android"]["email"] = "ईमेल"
        upload["api"]["Service is healthy"] = "सेवा ठीक है"

        # Act
        response = logged_admin.post(
            reverse("admin:languages_language_add"), form_data(translations_file=json_file(upload)), follow=True
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        language = Language.objects.get(code="hi")
        assert language.translations == {"android": {"email": "ईमेल"}, "api": {"Service is healthy": "सेवा ठीक है"}}
        assert language.version == FIRST_UPLOAD_VERSION
        assert "2 strings stored" in response.content.decode()

    def test_invalid_upload_is_rejected(self, logged_admin: AdminClient) -> None:
        response = logged_admin.post(
            reverse("admin:languages_language_add"),
            form_data(translations_file=json_file({"android": {"no_such_key": "x"}})),
        )

        assert response.status_code == HTTPStatus.OK
        assert "android: no_such_key: unknown key." in response.content.decode()
        assert not Language.objects.filter(code="hi").exists()

    def test_upload_on_existing_language_bumps_version(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="fr")

        logged_admin.post(
            reverse("admin:languages_language_change", args=(language.pk,)),
            form_data(
                code="fr",
                name="Français",
                english_name="French",
                flag="",
                position="2",
                translations_file=json_file({"android": {"email": "Courriel"}}),
            ),
        )

        language.refresh_from_db()
        assert language.translations == {"android": {"email": "Courriel"}}
        assert language.version == FIRST_UPLOAD_VERSION

    def test_saving_without_file_keeps_translations(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="fr")
        language.translations = {"android": {"email": "Courriel"}}
        language.save()

        logged_admin.post(
            reverse("admin:languages_language_change", args=(language.pk,)),
            form_data(code="fr", name="Français", english_name="French", flag="", position=str(NEW_POSITION)),
        )

        language.refresh_from_db()
        assert language.position == NEW_POSITION
        assert language.translations == {"android": {"email": "Courriel"}}
        assert language.version == 1

    def test_default_language_cannot_be_disabled(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="en")
        data = form_data(code="en", name="English", english_name="English", flag="", is_default="on")
        del data["is_enabled"]

        response = logged_admin.post(reverse("admin:languages_language_change", args=(language.pk,)), data)

        assert "The default language must be enabled." in response.content.decode()
        language.refresh_from_db()
        assert language.is_enabled

    def test_make_default(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="fr")

        logged_admin.get(reverse("admin:languages_language_make_default", args=(language.pk,)))

        assert list(Language.objects.filter(is_default=True).values_list("code", flat=True)) == ["fr"]

    def test_default_language_cannot_be_deleted(self, logged_admin: AdminClient) -> None:
        language = Language.objects.get(code="en")

        response = logged_admin.get(reverse("admin:languages_language_delete", args=(language.pk,)))

        assert response.status_code == HTTPStatus.FORBIDDEN
