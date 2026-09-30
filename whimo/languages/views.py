from http import HTTPStatus
from typing import Any

from django.utils.cache import patch_cache_control
from rest_framework import views
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from whimo.common.schemas.base import DataResponse
from whimo.languages import catalog, services
from whimo.languages.models import Language

# Public and cheap (cached): the apps call these before login, at every start.
CACHE_SECONDS = 300


class PublicView(views.APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = ()

    def finalize_response(self, request: Request, response: Response, *args: Any, **kwargs: Any) -> Response:
        response = super().finalize_response(request, response, *args, **kwargs)
        if response.status_code == HTTPStatus.OK:
            patch_cache_control(response, public=True, max_age=CACHE_SECONDS)
        return response


class LanguagesListView(PublicView):
    def get(self, *_: Any, **__: Any) -> Response:
        languages = services.enabled_languages()
        default = services.default_language(languages)
        data = {
            "default": default.code if default else None,
            "languages": [
                {
                    "code": language.code,
                    "name": language.name,
                    "english_name": language.english_name,
                    "flag": language.flag,
                    "version": language.version,
                }
                for language in languages
            ],
        }
        return DataResponse(data=data).as_response()


class LanguageStringsView(PublicView):
    """Strings uploaded for one platform of an enabled language. The apps put them on top of
    the strings they ship; a key missing here keeps the app's own text."""

    def get(self, _: Request, code: str, platform: str, *__: Any, **___: Any) -> Response:
        if platform not in catalog.PLATFORMS:
            raise NotFound
        language = services.match(code, services.enabled_languages())
        if language is None or language.code != code.lower():
            raise NotFound
        translations = Language.objects.filter(code=language.code).values_list("translations", flat=True).first()
        section = (translations or {}).get(platform) or {}
        response = DataResponse(data={"code": language.code, "version": language.version, "strings": section})
        return response.as_response(headers={"ETag": f'"{language.code}-{language.version}"'})
