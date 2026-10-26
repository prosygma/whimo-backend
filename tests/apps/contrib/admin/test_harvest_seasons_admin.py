from datetime import date
from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from django.urls import reverse

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import HarvestSeason

pytestmark = [pytest.mark.django_db]


class TestHarvestSeasonsAdmin:
    ADD_URL = "admin:db_harvestseason_add"
    CHANGE_URL = "admin:db_harvestseason_change"
    CHANGELIST_URL = "admin:db_harvestseason_changelist"

    def test_create_for_complete_commodity_group(self, admin_client: AdminClient) -> None:
        admin = UserFactory.create(superuser=True)
        group = CommodityGroupFactory.create()
        commodities = CommodityFactory.create_batch(size=2, group=group, with_harvest_season=False)
        admin_client.login(admin)

        response = admin_client.post(
            reverse(self.ADD_URL),
            data={
                "country": "Cameroon",
                "status": HarvestSeasonStatus.ACTIVE,
                "commodity_group": group.id,
                "year": 2026,
                "start_month": 9,
                "duration_months": 12,
                "_save": "Save",
            },
        )

        assert response.status_code == HTTPStatus.FOUND, response.content.decode()
        season = HarvestSeason.objects.get(commodity_group=group, year=2026)
        assert season.name == f"{group.name} 2026/27"
        assert season.country == "Cameroon"
        assert set(season.commodities.all()) == set(commodities)

    @pytest.mark.parametrize(
        ("status", "year", "start_month"),
        [
            (HarvestSeasonStatus.PAST, 2026, 3),
            (HarvestSeasonStatus.ACTIVE, 2026, 9),
        ],
    )
    def test_conflicting_season_for_a_group_rejected(
        self,
        admin_client: AdminClient,
        status: HarvestSeasonStatus,
        year: int,
        start_month: int,
    ) -> None:
        admin = UserFactory.create(superuser=True)
        commodity = CommodityFactory.create()
        admin_client.login(admin)

        response = admin_client.post(
            reverse(self.ADD_URL),
            data={
                "country": "",
                "status": status,
                "commodity_group": commodity.group_id,
                "year": year,
                "start_month": start_month,
                "duration_months": 12,
                "_save": "Save",
            },
        )

        assert response.status_code == HTTPStatus.OK
        assert "already covers this group, archive it first." in response.content.decode()
        assert not HarvestSeason.objects.filter(commodity_group=commodity.group_id, year=year).exists()

    def test_commodity_group_cannot_be_changed_after_creation(self, admin_client: AdminClient) -> None:
        admin = UserFactory.create(superuser=True)
        commodity = CommodityFactory.create()
        season = commodity.harvest_seasons.get()
        other_group = CommodityGroupFactory.create()
        admin_client.login(admin)

        response = admin_client.post(
            reverse(self.CHANGE_URL, args=(season.pk,)),
            data=self._change_data(season, other_group.id),
        )

        assert response.status_code == HTTPStatus.OK
        assert "The commodity group cannot be changed after creation." in response.content.decode()
        season.refresh_from_db()
        assert season.commodity_group_id == commodity.group_id

    def test_repeats_can_be_changed_on_an_existing_season(self, admin_client: AdminClient) -> None:
        admin = UserFactory.create(superuser=True)
        commodity = CommodityFactory.create(with_harvest_season=False)
        season = HarvestSeasonFactory.create(
            commodity_group=commodity.group,
            year=2026,
            start_month=9,
            duration_months=12,
            with_commodities=[commodity],
        )
        admin_client.login(admin)

        data = self._change_data(season, season.commodity_group_id)
        data["duration_months"] = 6

        response = admin_client.post(reverse(self.CHANGE_URL, args=(season.pk,)), data=data)

        assert response.status_code == HTTPStatus.FOUND, response.content.decode()
        season.refresh_from_db()
        assert season.duration_months == 6  # noqa: PLR2004 Magic value used in comparison
        assert season.start_date == date(2026, 9, 1)
        assert season.end_date == date(2027, 3, 1)
        assert season.name == f"{commodity.group.name} Sep-Feb 2026"

    def test_the_changelist_can_be_filtered_by_country(self, admin_client: AdminClient) -> None:
        admin = UserFactory.create(superuser=True)
        cameroon = HarvestSeasonFactory.create(country="Cameroon")
        brazil = HarvestSeasonFactory.create(country="Brazil")
        admin_client.login(admin)

        response = admin_client.get(reverse(self.CHANGELIST_URL), data={"country": "Cameroon"})
        listed = response.content.decode()

        assert response.status_code == HTTPStatus.OK, listed
        assert cameroon.name in listed
        assert brazil.name not in listed

    @staticmethod
    def _change_data(season: HarvestSeason, group_id: UUID) -> dict[str, Any]:
        return {
            "country": season.country,
            "status": season.status,
            "commodity_group": group_id,
            "year": season.year,
            "start_month": season.start_month,
            "duration_months": season.duration_months,
            "_save": "Save",
        }
