import importlib
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

migration = importlib.import_module("whimo.db.migrations.0010_stamp_chains_with_harvest_season")

pytestmark = [pytest.mark.django_db]


def transaction(
    created_at: datetime,
    commodity_id: UUID,
    seller_id: UUID | None = None,
    buyer_id: UUID | None = None,
    group_id: UUID | None = None,
) -> dict:
    return {
        "id": uuid4(),
        "created_at": created_at,
        "commodity_id": commodity_id,
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "group_id": group_id,
    }


class TestChainGrouping:
    def test_a_sale_joins_the_chain_of_the_volume_it_sells(self) -> None:
        # Arrange
        moment = datetime(2026, 1, 1, tzinfo=UTC)
        commodity, farmer, trader, buyer = uuid4(), uuid4(), uuid4(), uuid4()

        harvest = transaction(moment, commodity, buyer_id=trader)
        sale = transaction(moment + timedelta(days=1), commodity, seller_id=trader, buyer_id=buyer)
        unrelated = transaction(moment, uuid4(), buyer_id=farmer)

        # Act
        chains = migration.group_into_chains([harvest, sale, unrelated])

        # Assert
        assert len(chains) == 2  # noqa: PLR2004 Magic value used in comparison
        assert any({harvest["id"], sale["id"]} == {item["id"] for item in chain} for chain in chains.values())

    def test_a_conversion_keeps_its_inputs_and_outputs_together(self) -> None:
        # Arrange
        moment = datetime(2026, 1, 1, tzinfo=UTC)
        group, user = uuid4(), uuid4()

        conversion_input = transaction(moment, uuid4(), seller_id=user, group_id=group)
        conversion_output = transaction(moment, uuid4(), buyer_id=user, group_id=group)

        # Act
        chains = migration.group_into_chains([conversion_input, conversion_output])

        # Assert
        assert len(chains) == 1
        assert {item["id"] for item in next(iter(chains.values()))} == {
            conversion_input["id"],
            conversion_output["id"],
        }

    def test_a_later_purchase_does_not_pull_an_earlier_sale_into_its_chain(self) -> None:
        # Arrange
        moment = datetime(2026, 1, 1, tzinfo=UTC)
        commodity, trader, buyer = uuid4(), uuid4(), uuid4()

        sale = transaction(moment, commodity, seller_id=trader, buyer_id=buyer)
        later_purchase = transaction(moment + timedelta(days=1), commodity, buyer_id=trader)

        # Act
        chains = migration.group_into_chains([sale, later_purchase])

        # Assert
        assert len(chains) == 2  # noqa: PLR2004 Magic value used in comparison
