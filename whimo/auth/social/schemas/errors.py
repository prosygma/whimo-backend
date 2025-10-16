from django.utils.translation import gettext_lazy as _

from whimo.common.schemas.errors import Unauthorized


class OAuthError(Unauthorized):
    message = _("OAuth error")

    def __init__(self, errors: dict | None = None) -> None:
        self.errors = errors
