from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.db import DatabaseError
from django.utils import translation
from django.utils.translation import trans_real

from whimo.languages.models import Language

CACHE_KEY = "languages:enabled"
CACHE_TIMEOUT = 60 * 60


@dataclass(frozen=True)
class EnabledLanguage:
    code: str
    name: str
    english_name: str
    flag: str
    is_default: bool
    version: int
    api_messages: tuple[tuple[str, str], ...] = ()


def enabled_languages() -> list[EnabledLanguage]:
    """Languages offered in the apps, in picker order. Empty before the first migration."""
    languages: list[EnabledLanguage] | None = cache.get(CACHE_KEY)
    if languages is None:
        try:
            languages = [
                EnabledLanguage(
                    code=language.code,
                    name=language.name,
                    english_name=language.english_name,
                    flag=language.flag,
                    is_default=language.is_default,
                    version=language.version,
                    api_messages=_api_messages(language.translations),
                )
                for language in Language.objects.filter(is_enabled=True)
            ]
        except DatabaseError:
            return []
        cache.set(CACHE_KEY, languages, CACHE_TIMEOUT)
    return languages


def clear_cache() -> None:
    cache.delete(CACHE_KEY)


def default_language(languages: list[EnabledLanguage]) -> EnabledLanguage | None:
    return next((language for language in languages if language.is_default), languages[0] if languages else None)


def base(code: str) -> str:
    return code.lower().replace("_", "-").split("-")[0]


def match(code: str, languages: list[EnabledLanguage]) -> EnabledLanguage | None:
    """Enabled language for a code such as fr, fr-FR or fr_CA: exact match first, then same base."""
    code = code.lower().replace("_", "-")
    return next((lang for lang in languages if lang.code == code), None) or next(
        (lang for lang in languages if base(lang.code) == base(code)), None
    )


def resolve(accept_language: str, languages: list[EnabledLanguage]) -> EnabledLanguage | None:
    """Best enabled language for an Accept-Language header, else the default one."""
    for code, _quality in trans_real.parse_accept_lang_header(accept_language):
        if code != "*" and (language := match(code, languages)):
            return language
    return default_language(languages)


def django_code(code: str) -> str:
    """Code to activate in Django: the variant of settings.LANGUAGES with the same base
    (fr -> fr-FR, whose .po catalogue exists), or the code itself for a new language."""
    for variant, _name in settings.LANGUAGES:
        if variant.lower() == code:
            return variant
    for variant, _name in settings.LANGUAGES:
        if base(variant) == base(code):
            return variant
    return code


# Uploaded messages already merged into Django's catalogue of each language, in this process.
_applied_messages: dict[str, tuple[tuple[str, str], ...]] = {}


def activate(language: EnabledLanguage) -> None:
    """Activate a language in Django, with the `api` strings uploaded for it."""
    code = django_code(language.code)
    if _applied_messages.get(code) != language.api_messages:
        # Rebuild Django's catalogue for this language, then add the uploaded messages.
        trans_real._translations.pop(code, None)  # type: ignore[attr-defined]
        catalog = trans_real.translation(code)._catalog  # type: ignore[attr-defined]
        for msgid, msgstr in language.api_messages:
            catalog[msgid] = msgstr
        _applied_messages[code] = language.api_messages
    translation.activate(code)


def _api_messages(translations: object) -> tuple[tuple[str, str], ...]:
    api = translations.get("api") if isinstance(translations, dict) else None
    return tuple((key, value) for key, value in (api or {}).items() if isinstance(value, str))
