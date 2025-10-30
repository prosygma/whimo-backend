from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory

from tests.factories.users import GadgetFactory
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.contrib.tasks.cleanup import cleanup_unverified_gadgets
from whimo.db.models import Gadget

pytestmark = [pytest.mark.django_db]


class TestCleanupTasks:
    def test_cleanup_old_unverified_gadgets(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        old_date = DEFAULT_DATETIME - timedelta(days=31)
        recent_date = DEFAULT_DATETIME - timedelta(days=29)

        old_gadget_1 = GadgetFactory.create(is_verified=False)
        old_gadget_1.created_at = old_date
        old_gadget_1.save()

        old_gadget_2 = GadgetFactory.create(is_verified=False)
        old_gadget_2.created_at = old_date
        old_gadget_2.save()

        recent_gadget = GadgetFactory.create(is_verified=False)
        recent_gadget.created_at = recent_date
        recent_gadget.save()

        old_verified_gadget = GadgetFactory.create(is_verified=True)
        old_verified_gadget.created_at = old_date
        old_verified_gadget.save()

        # Act
        cleanup_unverified_gadgets()

        # Assert
        remaining_gadgets = Gadget.objects.all()
        remaining_ids = list(remaining_gadgets.values_list("id", flat=True))

        assert old_gadget_1.id not in remaining_ids
        assert old_gadget_2.id not in remaining_ids
        assert recent_gadget.id in remaining_ids
        assert old_verified_gadget.id in remaining_ids

    def test_cleanup_no_gadgets_to_delete(self) -> None:
        # Arrange
        GadgetFactory.create(is_verified=True)
        GadgetFactory.create(is_verified=False)
        initial_count = Gadget.objects.count()

        # Act
        cleanup_unverified_gadgets()

        # Assert
        final_count = Gadget.objects.count()
        assert final_count == initial_count
