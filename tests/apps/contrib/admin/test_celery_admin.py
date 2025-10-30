from http import HTTPStatus

import pytest
from django.urls import reverse
from django_celery_beat.models import IntervalSchedule, PeriodicTask

from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient

pytestmark = [pytest.mark.django_db]


class TestCeleryAdmin:
    CHANGE_URL = "admin:django_celery_beat_periodictask_change"
    CHANGELIST_URL = "admin:django_celery_beat_periodictask_changelist"

    def test_change(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        schedule = IntervalSchedule.objects.create(every=10, period=IntervalSchedule.SECONDS)
        entity = PeriodicTask.objects.create(name="test-task", task="test.task", interval=schedule)

        url = reverse(self.CHANGE_URL, args=(entity.pk,))

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
        assert str(entity.pk) in response_content

    def test_changelist(self, admin_client: AdminClient) -> None:
        # Arrange
        admin = UserFactory.create(superuser=True)
        schedule = IntervalSchedule.objects.create(every=10, period=IntervalSchedule.SECONDS)
        PeriodicTask.objects.create(name="test-task-1", task="test.task1", interval=schedule)
        PeriodicTask.objects.create(name="test-task-2", task="test.task2", interval=schedule)
        PeriodicTask.objects.create(name="test-task-3", task="test.task3", interval=schedule)

        url = reverse(self.CHANGELIST_URL)

        admin_client.login(admin)

        # Act
        response = admin_client.get(url)
        response_content = response.content.decode()

        # Assert
        assert response.status_code == HTTPStatus.OK, response_content
