from django.http import HttpRequest
from django.middleware.locale import LocaleMiddleware
from django.utils import translation

from whimo.languages import services


class LanguageMiddleware(LocaleMiddleware):
    """LocaleMiddleware limited to the languages enabled in the admin.

    The request language is the best enabled match of Accept-Language, else the default
    language chosen in the admin. Before the languages table exists, Django's own
    behaviour applies.
    """

    def process_request(self, request: HttpRequest) -> None:
        languages = services.enabled_languages()
        if not languages:
            super().process_request(request)
            return

        language = services.resolve(request.META.get("HTTP_ACCEPT_LANGUAGE", ""), languages)
        if language is None:  # pragma: no cover - resolve falls back to the first language
            super().process_request(request)
            return

        services.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
