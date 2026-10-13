import pytest

from tests.factories.commodities import CommodityFactory
from tests.factories.transactions import TransactionFactory
from tests.factories.users import UserFactory
from whimo.common.db_router import TestModeRouter
from whimo.common.test_mode import enable_test_mode
from whimo.db.models import Commodity, Transaction, User


@pytest.mark.django_db
class TestTestModeRouter:
    def test_routes_activity_models_to_test_mode_when_enabled(self) -> None:
        router = TestModeRouter()

        with enable_test_mode():
            assert router.db_for_read(Transaction) == "test_mode"
            assert router.db_for_write(Transaction) == "test_mode"

    def test_leaves_routing_alone_when_disabled(self) -> None:
        router = TestModeRouter()

        assert router.db_for_read(Transaction) is None

    def test_routes_reference_models_to_test_mode_when_enabled(self) -> None:
        router = TestModeRouter()

        with enable_test_mode():
            assert router.db_for_read(Commodity) == "test_mode"
            assert router.db_for_write(Commodity) == "test_mode"

    def test_allow_migrate_scopes_test_mode_to_activity_and_legacy_scaffold_models(self) -> None:
        # test_mode only ever gets tables for the routed activity models plus the
        # retired Season models Transaction used to reference (see
        # whimo/common/db_router.py) - never Commodity/User/HarvestSeason, whose
        # foreign keys must resolve to the real, populated public tables.
        router = TestModeRouter()

        assert router.allow_migrate("test_mode", "db", model_name="transaction") is True
        assert router.allow_migrate("test_mode", "db", model_name="season") is True
        assert router.allow_migrate("test_mode", "db", model_name="commodity") is False
        assert router.allow_migrate("test_mode", "db", model_name=None) is False
        assert router.allow_migrate("default", "db", model_name="commodity") is True
        assert router.allow_migrate("default", "db", model_name=None) is True


@pytest.mark.django_db(transaction=True, databases=["default", "test_mode"])
class TestTestModeRouterIntegration:
    def test_a_transaction_created_in_test_mode_lands_in_the_test_mode_alias(self) -> None:
        commodity = CommodityFactory.create()

        with enable_test_mode():
            transaction = TransactionFactory.create(commodity=commodity)

        assert Transaction.objects.using("test_mode").filter(pk=transaction.pk).exists()
        assert not Transaction.objects.using("default").filter(pk=transaction.pk).exists()

    def test_a_reference_model_written_in_test_mode_lands_in_public(self) -> None:
        with enable_test_mode():
            user = UserFactory.create(with_notification_settings=False)

        assert User.objects.using("default").filter(pk=user.pk).exists()
