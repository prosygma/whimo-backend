import pytest
from django.urls import Resolver404, resolve

pytestmark = [pytest.mark.django_db]


class TestTestModeUrls:
    def test_a_data_endpoint_is_mounted_under_the_test_prefix(self) -> None:
        normal = resolve("/api/v1/transactions/download/csv/")
        test = resolve("/api/v1/test/transactions/download/csv/")

        assert test.func == normal.func

    def test_auth_is_not_mounted_under_the_test_prefix(self) -> None:
        with pytest.raises(Resolver404):
            resolve("/api/v1/test/auth/otp/send/")
