import importlib
import json

import pytest
from django.http import QueryDict
from django.utils import translation

from whimo.common.utils import localized_name
from whimo.contrib.utils import NameVariantsWidget, name_variant_languages
from whimo.languages.models import Language

pytestmark = [pytest.mark.django_db]


class TestLocalizedName:
    @pytest.mark.parametrize(
        ("active", "variants", "expected"),
        [
            ("fr-fr", {"fr-FR": "Cacao"}, "Cacao"),
            ("fr", {"fr-FR": "Cacao"}, "Cacao"),
            ("fr-fr", {"fr": "Cacao"}, "Cacao"),
            ("hi", {"hi": "कोको"}, "कोको"),
            ("hi", {"fr-FR": "Cacao"}, "Cocoa"),
            ("fr-fr", {"fr-FR": ""}, "Cocoa"),
        ],
    )
    def test_matches_exact_then_base_language(self, active: str, variants: dict, expected: str) -> None:
        with translation.override(active):
            assert localized_name("Cocoa", variants) == expected


def _set_enabled(**states: bool) -> None:
    for code, enabled in states.items():
        Language.objects.filter(code=code).update(is_enabled=enabled)


class TestNameVariantLanguages:
    def test_lists_enabled_languages_and_keeps_unknown_keys(self) -> None:
        _set_enabled(en=True, fr=True, es=False)
        Language.objects.create(code="hi", name="हिन्दी", english_name="Hindi", is_enabled=False, position=4)

        choices = name_variant_languages({"fr-FR": "Cacao", "de": "Kakao"})

        assert choices == [
            ("en-US", "English"),
            ("fr-FR", "French"),
            ("de", "de"),
        ]

    def test_follows_language_positions(self) -> None:
        _set_enabled(en=True, fr=True, es=False)
        Language.objects.filter(code="fr").update(position=0)

        assert name_variant_languages({}) == [("fr-FR", "French"), ("en-US", "English")]


class TestNameVariantsWidget:
    def test_hides_variants_of_disabled_languages(self) -> None:
        _set_enabled(en=True, fr=True, es=False)
        variants = {"fr-FR": "Cacao", "es-ES": "Cacao ES", "de": "Kakao"}

        widget = NameVariantsWidget().get_context("name_variants", json.dumps(variants), None)["widget"]

        assert widget["rows"] == [("fr-FR", "Cacao"), ("de", "Kakao")]
        assert widget["hidden_rows"] == [("es-ES", "Cacao ES")]
        assert "es-ES" not in {code for code, _label in widget["languages"]}

    def test_shows_them_again_once_enabled(self) -> None:
        _set_enabled(en=True, fr=True, es=True)

        widget = NameVariantsWidget().get_context("name_variants", {"es-ES": "Cacao ES"}, None)["widget"]

        assert widget["rows"] == [("es-ES", "Cacao ES")]
        assert widget["hidden_rows"] == []

    def test_saving_keeps_hidden_variants(self) -> None:
        _set_enabled(en=True, fr=True, es=False)
        widget = NameVariantsWidget()
        html = widget.render("name_variants", {"fr-FR": "Cacao", "es-ES": "Cacao ES"})
        assert 'type="hidden" name="name_variants_language" value="es-ES"' in html

        data = QueryDict(mutable=True)
        data.setlist("name_variants_language", ["es-ES", "fr-FR"])
        data.setlist("name_variants_value", ["Cacao ES", "Chocolat"])

        assert json.loads(widget.value_from_datadict(data, {}, "name_variants")) == {
            "es-ES": "Cacao ES",
            "fr-FR": "Chocolat",
        }


class TestNameVariantsMigration:
    def test_codes_do_not_depend_on_settings(self, settings: object) -> None:
        migration = importlib.import_module("whimo.db.migrations.0004_name_variants_to_dict")
        settings.LANGUAGE_CODE = "fr-FR"  # type: ignore[attr-defined]
        settings.LANGUAGES = (("fr-FR", "French"), ("en-US", "English"))  # type: ignore[attr-defined]

        assert migration._variant_codes() == ["fr-FR", "es-ES"]
