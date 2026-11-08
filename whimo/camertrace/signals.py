from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from whimo.camertrace import services
from whimo.camertrace.models import GeodataOptions, TraceabilityRule


@receiver(post_save, sender=GeodataOptions)
@receiver(post_delete, sender=GeodataOptions)
@receiver(post_save, sender=TraceabilityRule)
@receiver(post_delete, sender=TraceabilityRule)
def clear_camertrace_cache(**_: Any) -> None:
    services.clear_cache()
