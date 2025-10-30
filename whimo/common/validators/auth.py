import re

from django.utils.translation import gettext_lazy as _
from email_validator import EmailNotValidError, validate_email


def normalize_email(email: str) -> str:
    try:
        validated = validate_email(email, check_deliverability=False)
    except EmailNotValidError as err:
        raise ValueError(_("Invalid email")) from err

    return validated.normalized


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def validate_password(password: str, min_length: int = 8) -> str:
    if len(password) < min_length:
        raise ValueError(_("Password must be at least %d characters long") % min_length)

    if not re.search(r"[A-Z]", password):
        raise ValueError(_("Password must contain at least one uppercase letter"))

    if not re.search(r"[a-z]", password):
        raise ValueError(_("Password must contain at least one lowercase letter"))

    if not re.search(r"\d", password):
        raise ValueError(_("Password must contain at least one number"))

    return password
