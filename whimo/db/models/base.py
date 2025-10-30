import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for this record."),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("Timestamp when this record was created."),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text=_("Timestamp when this record was last updated."),
    )

    class Meta:
        abstract = True

    def __str__(self) -> str:
        classname = self.__class__.__name__
        return f"{classname}: {self.short_id}"

    @property
    def short_id(self) -> str:
        return f"{self.id.hex[:4]}...{self.id.hex[-4:]}"
