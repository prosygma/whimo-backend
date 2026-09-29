import pytest
from pytest_mock import MockerFixture

from whimo.common.test_mode import enable_test_mode
from whimo.transactions.services import TransactionsService

pytestmark = [pytest.mark.django_db]


class TestInviteTestMode:
    def test_skips_invite_email_in_test_mode(self, mocker: MockerFixture) -> None:
        mock_send_email = mocker.patch("whimo.transactions.services.send_email")

        with enable_test_mode():
            TransactionsService._send_invite_email("someone@example.com")

        mock_send_email.delay.assert_not_called()

    def test_skips_invite_sms_in_test_mode(self, mocker: MockerFixture) -> None:
        mock_send_sms = mocker.patch("whimo.transactions.services.send_sms")

        with enable_test_mode():
            TransactionsService._send_invite_sms("+15551234567")

        mock_send_sms.delay.assert_not_called()

    def test_still_sends_invite_email_outside_test_mode(self, mocker: MockerFixture) -> None:
        mock_send_email = mocker.patch("whimo.transactions.services.send_email")

        TransactionsService._send_invite_email("someone@example.com")

        mock_send_email.delay.assert_called_once()
