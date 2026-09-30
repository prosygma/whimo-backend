from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from whimo.languages import services
from whimo.languages.models import Language


@receiver(post_save, sender=Language)
@receiver(post_delete, sender=Language)
def clear_languages_cache(**_: Any) -> None:
    services.clear_cache()
