from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AllValuesCheckboxFilter,
    AutocompleteSelectFilter,
    RangeDateFilter,
)
from unfold.decorators import action, display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from whimo.contrib.utils import ReadOnlyAdminMixin, change_link_with_icon, colored_text, get_admin_url, text_with_icon
from whimo.db.enums import GadgetType
from whimo.db.models import Balance, Gadget, Notification, NotificationSettings, Transaction, User


class GadgetInline(TabularInline):
    model = Gadget
    extra = 0
    fields = ("short_id", "identifier", "is_verified", "type")
    readonly_fields = ("short_id", "identifier", "type")

    tab = True
    hide_title = True

    @display(description="ID")
    def short_id(self, obj: Gadget) -> SafeString | None:
        return change_link_with_icon(obj)


class BalanceInline(ReadOnlyAdminMixin, TabularInline):
    model = Balance
    extra = 0
    fields = ("commodity_link", "volume")
    readonly_fields = ("commodity_link",)

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Balance]:
        return super().get_queryset(request).select_related("commodity")

    @display(description="Commodity", label=True)
    def commodity_link(self, obj: Balance) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))


class SellingInline(ReadOnlyAdminMixin, TabularInline):
    model = Transaction
    fk_name = "seller"
    extra = 0
    fields = ("short_id", "type", "status", "traceability", "commodity_link", "buyer_link", "created_at")
    readonly_fields = ("short_id", "commodity_link", "buyer_link", "created_at")
    verbose_name_plural = "Selling"

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Transaction]:
        return super().get_queryset(request).select_related("commodity", "buyer")

    @display(description="ID")
    def short_id(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Commodity", label=True)
    def commodity_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="Buyer", label=True)
    def buyer_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.buyer)


class BuyingInline(ReadOnlyAdminMixin, TabularInline):
    model = Transaction
    fk_name = "buyer"
    extra = 0
    fields = ("short_id", "type", "status", "traceability", "commodity_link", "seller_link", "created_at")
    readonly_fields = ("short_id", "commodity_link", "seller_link", "created_at")
    verbose_name_plural = "Buying"

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Transaction]:
        return super().get_queryset(request).select_related("commodity", "seller")

    @display(description="ID")
    def short_id(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Commodity", label=True)
    def commodity_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.commodity, text=str(obj.commodity))

    @display(description="Seller", label=True)
    def seller_link(self, obj: Transaction) -> SafeString | None:
        return change_link_with_icon(obj.seller)


class NotificationReceivedInline(ReadOnlyAdminMixin, TabularInline):
    model = Notification
    fk_name = "received_by"
    extra = 0
    fields = ("short_id", "type", "created_by_link", "created_at")
    readonly_fields = ("short_id", "created_by_link", "created_at")

    tab = True
    hide_title = True

    def get_queryset(self, request: HttpRequest) -> QuerySet[Notification]:
        return super().get_queryset(request).select_related("created_by")

    @display(description="ID")
    def short_id(self, obj: Notification) -> SafeString | None:
        return change_link_with_icon(obj)

    @display(description="Created By", label=True)
    def created_by_link(self, obj: Notification) -> SafeString | None:
        return change_link_with_icon(obj.created_by)


class NotificationSettingInline(ReadOnlyAdminMixin, TabularInline):
    model = NotificationSettings
    extra = 0
    fields = ("type", "is_enabled")

    tab = True
    hide_title = True


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin, SimpleHistoryAdmin):
    actions_detail = ("generate_access_token",)  # type: ignore
    list_display = (
        "short_id",
        "username",
        "is_deleted_labeled",
        "is_staff_labeled",
        "is_superuser_labeled",
        "date_joined",
    )
    list_filter = (
        "is_staff",
        "is_superuser",
        ("date_joined", RangeDateFilter),
        ("last_login", RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = ("id", "username", "gadgets__identifier")
    ordering = ("-date_joined",)

    fieldsets = (
        (_("User"), {"fields": ("username",)}),
        (_("Permissions"), {"fields": ("is_deleted", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Password"), {"fields": ("password",)}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at", "last_login", "date_joined")}),
    )

    readonly_fields = ("id", "created_at", "updated_at", "last_login", "date_joined")
    inlines = (
        GadgetInline,
        BalanceInline,
        SellingInline,
        BuyingInline,
        NotificationReceivedInline,
        NotificationSettingInline,
    )

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    @display(description="ID", ordering="id")
    def short_id(self, obj: User) -> str:
        return colored_text(obj.short_id)

    @display(
        description="Deleted",
        ordering="is_deleted",
        label={"True": "danger", "False": "success"},
    )
    def is_deleted_labeled(self, obj: User) -> str:
        return str(obj.is_deleted)

    @display(
        description="Staff",
        ordering="is_staff",
        label={"True": "success", "False": "danger"},
    )
    def is_staff_labeled(self, obj: User) -> str:
        return str(obj.is_staff)

    @display(
        description="Superuser",
        ordering="is_superuser",
        label={"True": "success", "False": "danger"},
    )
    def is_superuser_labeled(self, obj: User) -> str:
        return str(obj.is_superuser)

    @action(description="Access Token")
    def generate_access_token(self, request: HttpRequest, object_id: str) -> HttpResponse:
        response = redirect(get_admin_url(User, "change", args=(object_id,)))

        if not request.user.is_superuser:
            messages.error(request, "Only superusers can generate access tokens.")
            return response

        user = User.objects.get(pk=object_id)
        refresh = RefreshToken.for_user(user)

        token_html = mark_safe(
            f'<strong>Access Token</strong><br><code style="word-break: break-all;">{refresh.access_token}</code>'
        )
        messages.success(request, token_html)
        return response

    def has_delete_permission(self, _: HttpRequest, __: User | None = None) -> bool:
        return False


@admin.register(Gadget)
class GadgetAdmin(ModelAdmin, SimpleHistoryAdmin):
    list_display = ("short_id", "identifier", "type_labeled", "is_verified_labeled", "user_link", "created_at")
    list_filter = (
        "is_verified",
        ("type", AllValuesCheckboxFilter),
        ("user", AutocompleteSelectFilter),
        ("created_at", RangeDateFilter),
    )
    list_filter_submit = True
    list_select_related = ("user",)
    search_fields = ("id", "identifier", "user__username")
    ordering = ("-created_at",)

    fieldsets = (
        (_("Gadget"), {"fields": ("type", "identifier", "is_verified")}),
        (_("User"), {"fields": ("user",)}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("user",)

    @display(description="ID", ordering="id")
    def short_id(self, obj: Gadget) -> SafeString | None:
        return colored_text(obj.short_id)

    @display(description="User", ordering="user__id", label=True)
    def user_link(self, obj: Gadget) -> SafeString | None:
        return change_link_with_icon(obj.user)

    @display(
        description="Verified",
        ordering="is_verified",
        label={"True": "success", "False": "danger"},
    )
    def is_verified_labeled(self, obj: Gadget) -> str:
        return str(obj.is_verified)

    @display(description="Type", ordering="type", label=True)
    def type_labeled(self, obj: Gadget) -> str:
        icon = "phone" if obj.type == GadgetType.PHONE else "email"
        return text_with_icon(obj.type, icon)
