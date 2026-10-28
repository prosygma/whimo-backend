"""Seed rows the admin itself cannot create, so the e2e suite can exercise them.

`Transaction`, `Balance` and `Notification` use `ReadOnlyAdminMixin`, so they have no
add form. Without rows their changelists, filters, exports and detail actions are
untestable. This reuses the existing `tests/factories` rather than duplicating them.

Test-only: never run against a real database.
"""

from __future__ import annotations

import random
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction


class Command(BaseCommand):
    help = "Create Transaction/Balance/Notification rows for the admin e2e suite."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--users", type=int, default=4)
        parser.add_argument("--transactions", type=int, default=12)
        parser.add_argument("--balances", type=int, default=6)
        parser.add_argument("--notifications", type=int, default=6)

    @db_transaction.atomic
    def handle(self, *_: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError("Refusing to seed: DJANGO_DEBUG is not True.")

        try:
            from tests.factories.balances import BalanceFactory
            from tests.factories.base import BaseFactory
            from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
            from tests.factories.harvest_seasons import HarvestSeasonFactory
            from tests.factories.notifications import NotificationFactory
            from tests.factories.transactions import TransactionFactory
            from tests.factories.users import UserFactory
        except ImportError as exc:  # pragma: no cover
            raise CommandError(f"tests/factories not importable ({exc}); dev dependencies required.") from exc

        # BaseFactory ids are UUID(int=n) from a sequence, so a fresh offset per run
        # avoids primary-key collisions when seeding an already-populated database.
        # Every factory gets it, including the ones post-generation hooks call
        # (notification settings, gadgets...).
        offset = random.randrange(10**6, 10**9)
        pending = list(BaseFactory.__subclasses__())
        while pending:
            factory_class = pending.pop()
            factory_class.reset_sequence(offset)
            pending.extend(factory_class.__subclasses__())

        users = UserFactory.create_batch(options["users"])
        group = CommodityGroupFactory.create()
        # Transactions and balances take their commodity's first harvest season: one
        # active season for the group (a group allows only one) holds every commodity.
        season = HarvestSeasonFactory.create(commodity_group=group)
        commodities = CommodityFactory.create_batch(3, group=group, with_harvest_season=season)

        transactions = []
        for index in range(options["transactions"]):
            transactions.append(
                TransactionFactory.create(
                    commodity=commodities[index % len(commodities)],
                    seller=users[index % len(users)],
                    buyer=users[(index + 1) % len(users)],
                )
            )

        for index in range(options["balances"]):
            BalanceFactory.create(
                user=users[index % len(users)],
                commodity=commodities[index % len(commodities)],
            )

        for index in range(options["notifications"]):
            NotificationFactory.create(
                received_by=users[index % len(users)],
                created_by=users[(index + 1) % len(users)],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(users)} users, {len(commodities)} commodities, 1 harvest season, "
                f"{len(transactions)} transactions, {options['balances']} balances, "
                f"{options['notifications']} notifications."
            )
        )
