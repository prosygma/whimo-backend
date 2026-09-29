from django.db.models.enums import StrEnum


class GadgetType(StrEnum):
    PHONE = "phone"
    EMAIL = "email"


class OTPChannel(StrEnum):
    """How a verification code reached the user."""

    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
