from django.db.models.enums import StrEnum


class GadgetType(StrEnum):
    PHONE = "phone"
    EMAIL = "email"
