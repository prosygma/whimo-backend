from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from django.urls import reverse

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.users import UserFactory
from tests.helpers.clients import AdminClient
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import HarvestSeason

pytestmark = [pytest.mark.django_db]


class TestHarvestSeasonsAdmin:
    ADD_URL = "admin:db_harvestseason_add"
    CHANGE_URL = "admin:db_harvestseason_change"

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
        assert "Another season overlaps or is active for this group." in response.content.decode()
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
