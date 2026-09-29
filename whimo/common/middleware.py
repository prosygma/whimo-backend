from collections.abc import Callable
from http import HTTPStatus

from django.db import transaction
from django.http import HttpRequest, HttpResponse

from whimo.common.test_mode import enable_test_mode

TEST_MODE_PREFIX = "/api/v1/test/"


class TestModeMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not request.path.startswith(TEST_MODE_PREFIX):
            return self.get_response(request)

        with enable_test_mode(), transaction.atomic(using="test_mode"):
            response = self.get_response(request)
            if response.status_code >= HTTPStatus.BAD_REQUEST:
                transaction.set_rollback(True, using="test_mode")
            return response
