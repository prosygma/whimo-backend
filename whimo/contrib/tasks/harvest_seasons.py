import logging
from uuid import UUID

from celery import current_app
from django.db import transaction as db_transaction
from django.utils import timezone

from whimo.db.enums import HarvestSeasonStatus
from whimo.db.models import CommodityGroup, HarvestSeason
from whimo.harvest_seasons.services import HarvestSeasonsService

logger = logging.getLogger(__name__)


@current_app.task(autoretry_for=[Exception], retry_backoff=True, max_retries=3)
def transition_harvest_seasons() -> None:
    """Close every Active season whose end date has passed: archive the group's previous Past season
    and start the next one with the same country, commodity group and months, one year on.

    Does not look for or repair a commodity group that has no Active season at all (for example, one an
    admin moved out of Active by hand) - that stays a documented gap for an admin to notice and fix, not
    something this job auto-recovers.
    """
    today = timezone.now().date()
    elapsed_seasons = HarvestSeason.objects.filter(status=HarvestSeasonStatus.ACTIVE, end_date__lte=today)
    logger.info("Transitioning %d elapsed harvest seasons", elapsed_seasons.count())

    for season_id in elapsed_seasons.values_list("id", flat=True):
        try:
            _transition_one(season_id)
        except Exception:
            logger.exception("Failed to transition harvest season %s", season_id)


def _transition_one(season_id: UUID) -> None:
    with db_transaction.atomic():
        group_id = HarvestSeason.objects.filter(pk=season_id).values_list("commodity_group_id", flat=True).first()
        if group_id is None:
            return
        CommodityGroup.objects.select_for_update().get(pk=group_id)

        season = HarvestSeason.objects.filter(pk=season_id).first()
        if season is None or season.status != HarvestSeasonStatus.ACTIVE or season.end_date > timezone.now().date():
            return

        previous_past = HarvestSeason.objects.filter(
            commodity_group_id=group_id,
            status=HarvestSeasonStatus.PAST,
        ).first()
        if previous_past is not None:
            previous_past.status = HarvestSeasonStatus.ARCHIVED
            previous_past.save()

        season.status = HarvestSeasonStatus.PAST
        season.save()

        HarvestSeasonsService.create_next_season(season)
