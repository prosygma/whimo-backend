from enum import StrEnum


class HarvestSeasonStatus(StrEnum):
    ACTIVE = "active"
    PAST = "past"
    ARCHIVED = "archived"
