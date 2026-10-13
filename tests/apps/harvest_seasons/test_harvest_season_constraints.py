from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from tests.factories.commodities import CommodityFactory, CommodityGroupFactory
from tests.factories.harvest_seasons import HarvestSeasonCommodityFactory, HarvestSeasonFactory
from tests.helpers.constants import SMALL_BATCH_SIZE
from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import HarvestSeason, HarvestSeasonCommodity

pytestmark = [pytest.mark.django_db(transaction=True)]


class TestHarvestSeasonConstraints:
    def test_season_covers_the_whole_commodity_group(self) -> None:
        group = CommodityGroupFactory.create()
        commodities = CommodityFactory.create_batch(size=SMALL_BATCH_SIZE, group=group, with_harvest_season=False)
        season = HarvestSeasonFactory.create()

        HarvestSeasonCommodityFactory.create(harvest_season=season, commodity=commodities[0])

        assert set(season.commodities.all()) == set(commodities)

    def test_new_commodity_inherits_the_seasons_of_its_group(self) -> None:
        group = CommodityGroupFactory.create()
        existing = CommodityFactory.create(group=group, with_harvest_season=False)
        previous = HarvestSeasonFactory.create(
            start_date=date(2024, 9, 1),
            end_date=date(2025, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )
        active = HarvestSeasonFactory.create()
        HarvestSeasonCommodityFactory.create(harvest_season=previous, commodity=existing)
        HarvestSeasonCommodityFactory.create(harvest_season=active, commodity=existing)

        commodity = CommodityFactory.create(group=group, with_harvest_season=False)

        assert set(commodity.harvest_seasons.all()) == {previous, active}

    def test_commodity_with_seasons_cannot_move_to_another_group(self) -> None:
        commodity = CommodityFactory.create()
        commodity.group = CommodityGroupFactory.create()

        with pytest.raises(ValidationError):
            commodity.save()

    def test_coverage_cannot_move_to_another_season(self) -> None:
        commodity = CommodityFactory.create()
        link = HarvestSeasonCommodity.objects.get(commodity=commodity)
        link.harvest_season = HarvestSeasonFactory.create(
            start_date=date(2026, 9, 1),
            end_date=date(2027, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )

        with pytest.raises(ValidationError):
            link.save()

    def test_deleting_group_coverage_removes_every_commodity_link(self) -> None:
        group = CommodityGroupFactory.create()
        commodities = CommodityFactory.create_batch(size=SMALL_BATCH_SIZE, group=group, with_harvest_season=False)
        link = HarvestSeasonCommodityFactory.create(commodity=commodities[0])

        link.delete()

        assert not HarvestSeasonCommodity.objects.filter(commodity__group=group).exists()

    def test_overlapping_seasons_over_same_group_rejected(self) -> None:
        group = CommodityGroupFactory.create()
        commodities = CommodityFactory.create_batch(size=SMALL_BATCH_SIZE, group=group, with_harvest_season=False)
        current = HarvestSeasonFactory.create(status=HarvestSeasonStatus.PAST)
        overlapping = HarvestSeasonFactory.create(
            start_date=date(2026, 3, 1),
            end_date=date(2027, 3, 1),
        )
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodities[0])

        with pytest.raises(IntegrityError):
            HarvestSeasonCommodityFactory.create(harvest_season=overlapping, commodity=commodities[1])

    def test_overlapping_seasons_over_same_commodity_rejected(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        current = HarvestSeasonFactory.create(
            start_date=date(2025, 9, 1),
            end_date=date(2026, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )
        overlapping = HarvestSeasonFactory.create(
            start_date=date(2026, 3, 1),
            end_date=date(2027, 3, 1),
        )
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodity)

        # Act & Assert
        with pytest.raises(IntegrityError):
            HarvestSeasonCommodityFactory.create(harvest_season=overlapping, commodity=commodity)

    def test_adjacent_seasons_over_same_commodity_allowed(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        previous = HarvestSeasonFactory.create(
            start_date=date(2025, 9, 1),
            end_date=date(2026, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )
        current = HarvestSeasonFactory.create(start_date=date(2026, 9, 1), end_date=date(2027, 9, 1))

        # Act
        HarvestSeasonCommodityFactory.create(harvest_season=previous, commodity=commodity)
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodity)

        # Assert
        assert HarvestSeasonCommodity.objects.filter(commodity=commodity).count() == SMALL_BATCH_SIZE

    def test_second_active_season_over_same_commodity_rejected(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        current = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        another = HarvestSeasonFactory.create(start_date=date(2026, 9, 1), end_date=date(2027, 9, 1))
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodity)

        # Act & Assert
        with pytest.raises(IntegrityError):
            HarvestSeasonCommodityFactory.create(harvest_season=another, commodity=commodity)

    def test_overlapping_seasons_over_disjoint_commodities_allowed(self) -> None:
        # Arrange
        cocoa = CommodityFactory.create(with_harvest_season=False)
        coffee = CommodityFactory.create(with_harvest_season=False)
        cocoa_season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        coffee_season = HarvestSeasonFactory.create(start_date=date(2026, 3, 1), end_date=date(2027, 3, 1))

        # Act
        HarvestSeasonCommodityFactory.create(harvest_season=cocoa_season, commodity=cocoa)
        HarvestSeasonCommodityFactory.create(harvest_season=coffee_season, commodity=coffee)

        # Assert
        assert HarvestSeasonCommodity.objects.count() == SMALL_BATCH_SIZE

    def test_commodity_joins_season_once(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        harvest_season = HarvestSeasonFactory.create()
        HarvestSeasonCommodityFactory.create(harvest_season=harvest_season, commodity=commodity)

        # Act & Assert
        with pytest.raises(IntegrityError):
            HarvestSeasonCommodityFactory.create(harvest_season=harvest_season, commodity=commodity)

    def test_season_dates_kept_in_sync_with_commodities(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        harvest_season = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        HarvestSeasonCommodityFactory.create(harvest_season=harvest_season, commodity=commodity)

        # Act
        harvest_season.year = 2026
        harvest_season.start_month = 6
        harvest_season.duration_months = 6
        harvest_season.start_date = None  # type: ignore
        harvest_season.end_date = None  # type: ignore
        harvest_season.status = HarvestSeasonStatus.PAST
        harvest_season.save()

        # Assert
        harvest_season_commodity = HarvestSeasonCommodity.objects.get(commodity=commodity)
        assert harvest_season_commodity.period.upper == date(2026, 12, 1)
        assert harvest_season_commodity.status == HarvestSeasonStatus.PAST

    def test_start_date_after_end_date_rejected(self) -> None:
        # Act & Assert
        with pytest.raises(ValidationError):
            HarvestSeasonFactory.create(start_date=date(2026, 9, 1), end_date=date(2025, 9, 1))

    def test_transacting_status_is_descriptive(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        archived = HarvestSeasonFactory.create(
            start_date=date(2024, 9, 1),
            end_date=date(2025, 9, 1),
            status=HarvestSeasonStatus.ARCHIVED,
        )

        # Act
        with transaction.atomic():
            HarvestSeasonCommodityFactory.create(harvest_season=archived, commodity=commodity)

        # Assert
        assert HarvestSeasonCommodity.objects.get(commodity=commodity).status == HarvestSeasonStatus.ARCHIVED


class TestHarvestSeasonValidation:
    def test_overlapping_commodity_reported_as_validation_error(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        current = HarvestSeasonFactory.create(
            start_date=date(2025, 9, 1),
            end_date=date(2026, 9, 1),
            status=HarvestSeasonStatus.PAST,
        )
        overlapping = HarvestSeasonFactory.create(start_date=date(2026, 3, 1), end_date=date(2027, 3, 1))
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodity)

        # Act & Assert
        with pytest.raises(ValidationError):
            HarvestSeasonCommodity(harvest_season=overlapping, commodity=commodity).full_clean()

    def test_second_active_season_reported_as_validation_error(self) -> None:
        # Arrange
        commodity = CommodityFactory.create(with_harvest_season=False)
        current = HarvestSeasonFactory.create(start_date=date(2025, 9, 1), end_date=date(2026, 9, 1))
        another = HarvestSeasonFactory.create(start_date=date(2026, 9, 1), end_date=date(2027, 9, 1))
        HarvestSeasonCommodityFactory.create(harvest_season=current, commodity=commodity)

        # Act & Assert
        with pytest.raises(ValidationError):
            HarvestSeasonCommodity(harvest_season=another, commodity=commodity).full_clean()

    def test_start_date_after_end_date_reported_as_validation_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValidationError):
            HarvestSeason(name="Broken", start_date=date(2026, 9, 1), end_date=date(2025, 9, 1)).full_clean()
