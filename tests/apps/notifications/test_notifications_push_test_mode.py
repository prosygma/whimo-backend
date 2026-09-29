import pytest
from pytest_mock import MockerFixture

from tests.factories.notifications import NotificationFactory
from whimo.common.test_mode import enable_test_mode
from whimo.notifications.services.notifications_push import NotificationsPushService

pytestmark = [pytest.mark.django_db]


class TestNotificationsPushTestMode:
    def test_skips_delivery_for_a_test_mode_request(self, mocker: MockerFixture) -> None:
        notification = NotificationFactory.create()
        mock_gcm = mocker.patch("whimo.notifications.services.notifications_push.send_gcm_push")
        mock_apns = mocker.patch("whimo.notifications.services.notifications_push.send_apns_push")

        with enable_test_mode():
            NotificationsPushService.send_push([notification.id])

        mock_gcm.delay.assert_not_called()
        mock_apns.delay.assert_not_called()
