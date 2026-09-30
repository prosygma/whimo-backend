import importlib

import pytest
from django.utils import translation

from whimo.common.utils import localized_name
from whimo.contrib.utils import name_variant_languages
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


class TestNameVariantLanguages:
    def test_lists_admin_languages_and_keeps_unknown_keys(self) -> None:
        Language.objects.create(code="hi", name="हिन्दी", english_name="Hindi", is_enabled=False, position=4)

        choices = name_variant_languages({"fr-FR": "Cacao", "de": "Kakao"})

        assert choices == [
            ("en-US", "English"),
            ("fr-FR", "French"),
            ("es-ES", "Spanish"),
            ("hi", "Hindi"),
            ("de", "de"),
        ]


class TestNameVariantsMigration:
    def test_codes_do_not_depend_on_settings(self, settings: object) -> None:
        migration = importlib.import_module("whimo.db.migrations.0004_name_variants_to_dict")
        settings.LANGUAGE_CODE = "fr-FR"  # type: ignore[attr-defined]
        settings.LANGUAGES = (("fr-FR", "French"), ("en-US", "English"))  # type: ignore[attr-defined]

        assert migration._variant_codes() == ["fr-FR", "es-ES"]
