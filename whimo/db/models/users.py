from secrets import token_hex
from typing import cast
from uuid import UUID

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from whimo.db.enums import GadgetType
from whimo.db.enums.notifications import NotificationType
from whimo.db.models import BaseModel, NotificationSettings

USER_GADGETS_FIELD = "_gadgets"
_not_set = object()


class CustomUserManager(UserManager):
    def create_custom_user(self, password: str | None) -> "User":
        user = self.create_user(  # type: ignore
            username=self.create_username(),
            password=password,
        )
        self.create_default_notification_settings(user.pk)
        return user  # type: ignore

    def create_default_notification_settings(self, user_id: UUID) -> None:
        settings_to_create = [
            NotificationSettings(
                user_id=user_id,
                type=notification_type,
                is_enabled=True,
            )
            for notification_type in NotificationType
        ]
        NotificationSettings.objects.bulk_create(settings_to_create, ignore_conflicts=True)

    def generate_prefetch_gadgets(self, relation: str = "", include_unverified: bool = False) -> models.Prefetch:
        gadgets_queryset = Gadget.objects.all()
        if not include_unverified:
            gadgets_queryset = gadgets_queryset.filter(is_verified=True)

        return models.Prefetch(lookup=f"{relation}gadgets", to_attr=USER_GADGETS_FIELD, queryset=gadgets_queryset)

    def prefetch_gadgets(self, relation: str = "", include_unverified: bool = False) -> QuerySet["User"]:
        queryset = self.prefetch_related(self.generate_prefetch_gadgets(relation, include_unverified))
        return cast(QuerySet, queryset)

    @classmethod
    def create_username(cls, suffix_bytes: int = 4) -> str:
        return token_hex(suffix_bytes)


class User(AbstractUser, BaseModel):
    is_deleted = models.BooleanField(
        default=False,
        help_text=_("Indicates whether this user has been soft deleted"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "password",
            "created_at",
            "updated_at",
            "date_joined",
        ),
        table_name="users_history",
    )

    objects = CustomUserManager()  # type: ignore

    @property
    def gadgets_list(self) -> list["Gadget"]:
        gadgets = getattr(self, USER_GADGETS_FIELD, _not_set)
        if gadgets is _not_set:
            raise AttributeError("`.objects.prefetch_gadgets` must be called to use `gadgets_list`.")
        return cast(list, gadgets)

    class Meta:
        db_table = "users"
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ("-username",)

    def __str__(self) -> str:
        return f"User: {self.short_id}"


class Gadget(BaseModel):
    type = models.CharField(
        max_length=10,
        choices=[(item.value, item.name) for item in GadgetType],
        help_text=_("Type of contact method (phone or email)"),
    )
    identifier = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Contact identifier (e.g. email address or phone number)"),
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Indicates whether this contact method has been verified by the user"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="gadgets",
        help_text=_("The user this gadget belongs to"),
    )

    history = HistoricalRecords(
        excluded_fields=(
            "pk",
            "created_at",
            "updated_at",
        ),
        table_name="gadgets_history",
    )

    class Meta:
        db_table = "gadgets"
        verbose_name = _("Gadget")
        verbose_name_plural = _("Gadgets")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.get_type_display()}: {self.identifier}"
