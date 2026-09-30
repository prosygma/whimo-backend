import json

import pytest

from whimo.languages import catalog

pytestmark = [pytest.mark.django_db]


def english(platform: str, *path: str) -> str:
    return catalog.lookup(catalog.template(), platform, path)


class TestTemplate:
    def test_template_has_every_platform(self) -> None:
        template = catalog.template()

        assert set(template) == set(catalog.PLATFORMS)
        assert catalog.template_size() == catalog.count(template)
        assert english("web", "common", "email")

    def test_download_fills_missing_strings_with_english(self) -> None:
        pack = catalog.download("hi", {"android": {"email": "ईमेल"}})

        assert pack["android"]["email"] == "ईमेल"
        assert pack["ios"] == catalog.template()["ios"]
        assert catalog.count(pack) == catalog.template_size()


class TestPlaceholders:
    def test_extracts_every_syntax(self) -> None:
        text = "%s %1$s %@ %d %(app_name)s {{count}} <0>a</0> <btn>"

        assert sorted(catalog.placeholders(text).elements()) == sorted(
            ["%s", "%1$s", "%@", "%d", "%(app_name)s", "{{count}}", "<0>", "</0>", "<btn>"]
        )

    def test_percent_sign_in_prose_is_not_a_placeholder(self) -> None:
        assert not catalog.placeholders("100 % des parcelles, 50% sure")


class TestParseUpload:
    def test_new_language_keeps_translated_strings_only(self) -> None:
        upload = catalog.download("en", {})
        translated = [("android", "email"), ("web", "common", "email")]
        upload["android"]["email"] = "ईमेल"
        upload["web"]["common"]["email"] = "ईमेल"

        result = catalog.parse_upload("hi", json.dumps(upload))

        assert result.is_valid, result.errors
        assert result.translations == {"web": {"common": {"email": "ईमेल"}}, "android": {"email": "ईमेल"}}
        assert result.stored == len(translated)
        assert result.unchanged == catalog.template_size() - len(translated)

    def test_shipped_language_stores_corrections_only(self) -> None:
        upload = catalog.download("fr", {})
        upload["android"]["email"] = "Courriel"

        result = catalog.parse_upload("fr", json.dumps(upload))

        assert result.is_valid, result.errors
        assert result.translations == {"android": {"email": "Courriel"}}

    def test_previous_uploads_are_kept_unless_reset(self) -> None:
        previous = {"android": {"email": "Courriel"}, "ios": {"general.keyboard.toolbar.done": "Fini"}}
        shipped_done = catalog.lookup(catalog.shipped("fr"), "ios", ("general.keyboard.toolbar.done",))

        result = catalog.parse_upload(
            "fr", json.dumps({"ios": {"general.keyboard.toolbar.done": shipped_done}}), previous=previous
        )

        assert result.translations == {"android": {"email": "Courriel"}}

    def test_empty_values_are_ignored(self) -> None:
        result = catalog.parse_upload("hi", json.dumps({"android": {"email": "  "}}))

        assert result.is_valid
        assert result.translations == {}

    def test_rejects_invalid_json(self) -> None:
        result = catalog.parse_upload("hi", b"{not json")

        assert not result.is_valid
        assert "not valid JSON" in result.errors[0]

    def test_rejects_unknown_sections_and_keys(self) -> None:
        upload = {"desktop": {}, "android": {"no_such_key": "x"}, "web": {"common": {"nope": "x"}}}

        result = catalog.parse_upload("hi", json.dumps(upload))

        assert not result.is_valid
        assert result.translations == {}
        assert any("desktop" in error for error in result.errors)
        assert any("android: no_such_key" in error for error in result.errors)
        assert any("web: common.nope" in error for error in result.errors)

    def test_rejects_changed_placeholders(self) -> None:
        key = next(key for key, value in catalog.template()["android"].items() if "%s" in value)

        result = catalog.parse_upload("hi", json.dumps({"android": {key: "कोई प्लेसहोल्डर नहीं"}}))

        assert not result.is_valid
        assert f"android: {key}" in result.errors[0]
        assert "%s" in result.errors[0]

    def test_rejects_non_text_values(self) -> None:
        result = catalog.parse_upload("hi", json.dumps({"android": {"email": 12}}))

        assert not result.is_valid
