from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from whimo.db.models.base import BaseModel


def default_template_languages() -> dict[str, str]:
    return {"en-us": "en_US", "fr-fr": "fr", "es-es": "es"}


class WhatsAppSettings(BaseModel):
    """Credentials of the Meta WhatsApp Cloud API, entered by an administrator.

    Single row (see `load`). When active, phone verification codes are sent
    through WhatsApp instead of SMS.
    """

    is_enabled = models.BooleanField(
        default=False,
        help_text=_("Send phone verification codes through WhatsApp instead of SMS."),
    )
    api_version = models.CharField(
        max_length=16,
        default="v21.0",
        help_text=_("Graph API version, for example v21.0."),
    )
    phone_number_id = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("Phone number ID of the sender, from WhatsApp Manager > API Setup."),
    )
    access_token = models.TextField(
        blank=True,
        help_text=_("Permanent access token of a system user with the whatsapp_business_messaging permission."),
    )
    template_name = models.CharField(
        max_length=512,
        blank=True,
        help_text=_('Name of an approved message template of the "Authentication" category, with a copy-code button.'),
    )
    template_languages = models.JSONField(
        default=default_template_languages,
        blank=True,
        help_text=_(
            "Template language to use for each app language, for example "
            '{"en-us": "en_US", "fr-fr": "fr", "es-es": "es"}.'
        ),
    )
    test_phone_number = models.CharField(
        max_length=32,
        blank=True,
        help_text=_('Number that receives the code sent by "Send test message", with country code.'),
    )
    last_test_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_test_status = models.TextField(blank=True, editable=False)

    class Meta:
        verbose_name = _("WhatsApp settings")
        verbose_name_plural = _("WhatsApp settings")

    def __str__(self) -> str:
        return str(_("WhatsApp settings"))

    @classmethod
    def load(cls) -> "WhatsAppSettings":
        instance = cls.objects.order_by("created_at").first()
        return instance if instance is not None else cls.objects.create()

    @property
    def is_active(self) -> bool:
        return bool(
            self.is_enabled and self.api_version and self.phone_number_id and self.access_token and self.template_name
        )

    def template_language(self, language: str | None) -> str:
        languages: dict[str, Any] = self.template_languages or {}
        if language:
            code = language.lower()
            if code in languages:
                return str(languages[code])
            for key, value in languages.items():
                if key.split("-")[0] == code.split("-")[0]:
                    return str(value)
        return str(next(iter(languages.values()), "en_US"))
