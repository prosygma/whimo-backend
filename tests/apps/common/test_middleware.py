from decimal import Decimal
from http import HTTPStatus

import pytest
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

from tests.factories.balances import BalanceFactory
from tests.factories.commodities import CommodityFactory
from tests.factories.users import UserFactory
from whimo.common.middleware import TestModeMiddleware
from whimo.common.test_mode import is_test_mode
from whimo.db.models import Balance

pytestmark = [pytest.mark.django_db(transaction=True, databases=["default", "test_mode"])]


class TestTestModeMiddleware:
    def test_enables_test_mode_for_test_prefix(self, rf: RequestFactory) -> None:
        seen = {}

        def get_response(_request: HttpRequest) -> HttpResponse:
            seen["test_mode"] = is_test_mode()
            return HttpResponse()

        middleware = TestModeMiddleware(get_response)
        middleware(rf.get("/api/v1/test/transactions/"))

        assert seen["test_mode"] is True

    def test_leaves_test_mode_off_for_normal_prefix(self, rf: RequestFactory) -> None:
        seen = {}

        def get_response(_request: HttpRequest) -> HttpResponse:
            seen["test_mode"] = is_test_mode()
            return HttpResponse()

        middleware = TestModeMiddleware(get_response)
        middleware(rf.get("/api/v1/transactions/"))

        assert seen["test_mode"] is False

    def test_resets_test_mode_after_the_view_raises(self, rf: RequestFactory) -> None:
        def get_response(_request: HttpRequest) -> HttpResponse:
            raise ValueError("boom")

        middleware = TestModeMiddleware(get_response)
        with pytest.raises(ValueError, match="boom"):
            middleware(rf.get("/api/v1/test/transactions/"))

        assert is_test_mode() is False

    def test_runs_a_test_mode_request_inside_a_test_mode_transaction(self, rf: RequestFactory) -> None:
        seen = {}

        def get_response(_request: HttpRequest) -> HttpResponse:
            seen["in_atomic_block"] = transaction.get_connection("test_mode").in_atomic_block
            return HttpResponse()

        middleware = TestModeMiddleware(get_response)
        middleware(rf.get("/api/v1/test/transactions/"))

        assert seen["in_atomic_block"] is True

    @pytest.mark.parametrize(
        ("status", "is_kept"),
        [
            (HTTPStatus.OK, True),
            (HTTPStatus.BAD_REQUEST, False),
            (HTTPStatus.CONFLICT, False),
            (HTTPStatus.INTERNAL_SERVER_ERROR, False),
        ],
    )
    def test_keeps_test_mode_writes_of_successful_requests_only(
        self,
        rf: RequestFactory,
        status: HTTPStatus,
        is_kept: bool,
    ) -> None:
        user = UserFactory.create()
        commodity = CommodityFactory.create()

        def get_response(_request: HttpRequest) -> HttpResponse:
            BalanceFactory.create(user=user, commodity=commodity, volume=Decimal("1.00"))
            return HttpResponse(status=status)

        middleware = TestModeMiddleware(get_response)
        middleware(rf.post("/api/v1/test/transactions/producer/"))

        assert Balance.objects.using("test_mode").filter(user=user).exists() is is_kept
