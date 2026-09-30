from django.apps import AppConfig


class CamerTraceConfig(AppConfig):
    """Cameroon-only setup, kept apart so that its migrations never collide with EFI's."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "whimo.camertrace"
    label = "camertrace"
