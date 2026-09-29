from datetime import date

from whimo.common.schemas.dto import BaseModelDTO
from whimo.db.enums import HarvestSeasonStatus


class HarvestSeasonDTO(BaseModelDTO):
    name: str
    start_date: date
    end_date: date
    status: HarvestSeasonStatus
