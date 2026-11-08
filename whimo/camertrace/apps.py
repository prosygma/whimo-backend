from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CamerTraceConfig(AppConfig):
    """Cameroon-only setup, kept apart so that its migrations never collide with EFI's."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "whimo.camertrace"
    label = "camertrace"
    verbose_name = _("Settings")

    def ready(self) -> None:
        from whimo.camertrace import signals  # noqa: F401
