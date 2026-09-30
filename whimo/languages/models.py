from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from whimo.db.models.base import BaseModel

language_code_validator = RegexValidator(
    r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$",
    _("Use a lowercase ISO 639 code, optionally with a region: hi, fr, pt-br."),
)


class Language(BaseModel):
    """A language the apps offer, with the translations uploaded by an administrator.

    The apps ship their own strings for a few languages. `translations` only holds what an
    administrator uploaded on top of them: the whole text of a language the apps don't ship,
    or corrections to one they do. It has one section per platform (see catalog.PLATFORMS).
    """

    code = models.CharField(
        max_length=16,
        unique=True,
        validators=[language_code_validator],
        help_text=_("ISO 639 code, for example hi. The apps use it to pick their strings."),
    )
    name = models.CharField(
        max_length=64,
        help_text=_("Name of the language in that language, as shown in the language picker, for example हिन्दी."),
    )
    english_name = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("Name of the language in English, for example Hindi."),
    )
    flag = models.CharField(
        max_length=16,
        blank=True,
        help_text=_("Optional flag emoji shown next to the name, for example 🇮🇳."),
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text=_("Offer this language in the apps."),
    )
    is_default = models.BooleanField(
        default=False,
        help_text=_("Language used when the user's language is not offered."),
    )
    position = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in the language picker, lowest first."),
    )
    translations = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Uploaded strings, one section per platform."),
    )
    version = models.PositiveIntegerField(
        default=1,
        editable=False,
        help_text=_("Increases with each upload, so that the apps download the new strings."),
    )

    class Meta:
        ordering = ("position", "code")
        verbose_name = _("language")
        verbose_name_plural = _("languages")
        constraints = (
            models.UniqueConstraint(
                fields=("is_default",),
                condition=Q(is_default=True),
                name="languages_single_default",
            ),
        )

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        with transaction.atomic():
            if self.is_default:
                Language.objects.exclude(pk=self.pk).filter(is_default=True).update(is_default=False)
            super().save(*args, **kwargs)

    def clean(self) -> None:
        super().clean()
        self.code = self.code.strip().lower()
        if self.is_default and not self.is_enabled:
            raise ValidationError({"is_enabled": _("The default language must be enabled.")})
