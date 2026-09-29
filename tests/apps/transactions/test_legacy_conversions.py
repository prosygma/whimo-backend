import importlib
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from django.apps import apps
from freezegun.api import FrozenDateTimeFactory

from tests.factories.commodities import CommodityFactory
from tests.factories.harvest_seasons import HarvestSeasonFactory
from tests.factories.transactions import TransactionFactory, create_conversion
from tests.factories.users import UserFactory
from tests.helpers.constants import DEFAULT_DATETIME
from whimo.db.enums import TransactionStatus, TransactionType
from whimo.db.models import Transaction
from whimo.db.storages.transactions import TransactionsStorage

migration = importlib.import_module("whimo.db.migrations.0016_group_legacy_conversions")

pytestmark = [pytest.mark.django_db]


class TestGroupLegacyConversionsMigration:
    def test_a_single_season_cluster_becomes_one_conversion(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        conversion = create_conversion(user, None, inputs=[Decimal(10)], outputs=[Decimal(5), Decimal(3)])

        # Act
        migration.group_legacy_conversions(apps, None)

        # Assert
        group_ids = {
            transaction.group_id for transaction in Transaction.objects.filter(pk__in=[row.pk for row in conversion])
        }
        assert len(group_ids) == 1
        assert None not in group_ids

    def test_a_cluster_across_two_seasons_stays_ungrouped(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        user = UserFactory.create()
        conversion = create_conversion(user, None, inputs=[Decimal(10)], outputs=[Decimal(5)])

        other_season = HarvestSeasonFactory.create()
        output = conversion[1]
        output.harvest_season = other_season
        output.commodity = CommodityFactory.create(with_harvest_season=other_season)
        output.save(update_fields=["harvest_season", "commodity"])

        # Act
        migration.group_legacy_conversions(apps, None)

        # Assert
        assert not Transaction.objects.filter(group_id__isnull=False).exists()

    def test_clusters_of_two_users_stay_apart(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        first = create_conversion(UserFactory.create(), None, inputs=[Decimal(10)], outputs=[Decimal(5)])
        second = create_conversion(UserFactory.create(), None, inputs=[Decimal(10)], outputs=[Decimal(5)])

        # Act
        migration.group_legacy_conversions(apps, None)

        # Assert
        groups = {
            transaction.pk: transaction.group_id
            for transaction in Transaction.objects.filter(pk__in=[row.pk for row in first + second])
        }
        assert groups[first[0].pk] == groups[first[1].pk]
        assert groups[second[0].pk] == groups[second[1].pk]
        assert groups[first[0].pk] != groups[second[0].pk]

    def test_a_second_run_changes_nothing(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        create_conversion(UserFactory.create(), None, inputs=[Decimal(10)], outputs=[Decimal(5)])
        migration.group_legacy_conversions(apps, None)
        groups = dict(Transaction.objects.values_list("pk", "group_id"))

        # Act
        migration.group_legacy_conversions(apps, None)

        # Assert
        assert dict(Transaction.objects.values_list("pk", "group_id")) == groups


class TestLegacyConversionChain:
    def test_an_output_without_group_id_pulls_no_inputs(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        owner, stranger = UserFactory.create(), UserFactory.create()
        harvest_season = HarvestSeasonFactory.create()
        commodity = CommodityFactory.create(with_harvest_season=harvest_season)

        stranger_input = TransactionFactory.create(
            type=TransactionType.CONVERSION,
            status=TransactionStatus.ACCEPTED,
            group_id=None,
            commodity=commodity,
            harvest_season=harvest_season,
            volume=Decimal(-10),
            seller=stranger,
            buyer=None,
            created_by=stranger,
        )

        freezer.move_to(DEFAULT_DATETIME + timedelta(hours=1))
        output = TransactionFactory.create(
            type=TransactionType.CONVERSION,
            status=TransactionStatus.ACCEPTED,
            group_id=None,
            commodity=commodity,
            harvest_season=harvest_season,
            volume=Decimal(5),
            seller=None,
            buyer=owner,
            created_by=owner,
        )

        # Act
        chain = TransactionsStorage.get_chain_transactions(output.id)

        # Assert
        assert {transaction.pk for transaction in chain} == {output.pk}
        assert stranger_input.pk not in {transaction.pk for transaction in chain}

    def test_a_grouped_output_still_pulls_its_own_inputs(self, freezer: FrozenDateTimeFactory) -> None:
        # Arrange
        freezer.move_to(DEFAULT_DATETIME)

        owner = UserFactory.create()
        conversion_input, output = create_conversion(owner, UUID(int=1), inputs=[Decimal(10)], outputs=[Decimal(5)])

        # Act
        chain = TransactionsStorage.get_chain_transactions(output.id)

        # Assert
        assert {transaction.pk for transaction in chain} == {output.pk, conversion_input.pk}
