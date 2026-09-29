import secrets
import string
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.utils import timezone, translation
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.widgets import INPUT_CLASSES

from whimo.common.whatsapp import WhatsAppClient, WhatsAppError, WhatsAppTemporaryError
from whimo.contrib.utils import get_admin_url
from whimo.db.models import WhatsAppSettings


class WhatsAppSettingsForm(forms.ModelForm):
    # Never sent back to the browser; leaving the field empty keeps the saved token.
    access_token = forms.CharField(
        label=_("Access token"),
        required=False,
        widget=forms.PasswordInput(render_value=False, attrs={"class": " ".join(INPUT_CLASSES)}),
        help_text=_("Leave empty to keep the current token."),
    )

    class Meta:
        model = WhatsAppSettings
        fields = (
            "is_enabled",
            "api_version",
            "phone_number_id",
            "access_token",
            "template_name",
            "template_languages",
            "test_phone_number",
        )

    def clean_access_token(self) -> str:
        token = self.cleaned_data.get("access_token", "").strip()
        return token or (self.instance.access_token if self.instance.pk else "")

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("is_enabled"):
            required = ("api_version", "phone_number_id", "access_token", "template_name")
            for field in required:
                if not cleaned.get(field):
                    self.add_error(field, _("Required to enable WhatsApp."))
        return cleaned


@admin.register(WhatsAppSettings)
class WhatsAppSettingsAdmin(ModelAdmin):
    form = WhatsAppSettingsForm
    actions_detail = ("send_test_message",)  # type: ignore

    fieldsets = (
        (_("Status"), {"fields": ("is_enabled",)}),
        (
            _("Meta WhatsApp Cloud API"),
            {"fields": ("api_version", "phone_number_id", "access_token", "template_name", "template_languages")},
        ),
        (_("Test"), {"fields": ("test_phone_number", "last_test_at", "last_test_status")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )
    readonly_fields = ("last_test_at", "last_test_status", "id", "created_at", "updated_at")

    def has_add_permission(self, _: HttpRequest) -> bool:
        return not WhatsAppSettings.objects.exists()

    def has_delete_permission(self, _: HttpRequest, __: WhatsAppSettings | None = None) -> bool:
        return False

    def changelist_view(self, _: HttpRequest, __: dict[str, Any] | None = None) -> HttpResponse:
        # A single row: go straight to its form.
        config = WhatsAppSettings.load()
        return HttpResponseRedirect(get_admin_url(WhatsAppSettings, "change", args=(config.pk,)))

    @action(description=_("Send test message"))
    def send_test_message(self, request: HttpRequest, object_id: str) -> HttpResponse:
        response = redirect(get_admin_url(WhatsAppSettings, "change", args=(object_id,)))
        config = WhatsAppSettings.objects.get(pk=object_id)

        if not config.test_phone_number:
            messages.error(request, _("Save a test phone number first."))
            return response

        required = ("api_version", "phone_number_id", "access_token", "template_name")
        missing = [field for field in required if not getattr(config, field)]
        if missing:
            messages.error(request, _("Missing settings: %s") % ", ".join(missing))
            return response

        code = "".join(secrets.choice(string.digits) for _ in range(6))
        try:
            message_id = WhatsAppClient(config).send_otp(config.test_phone_number, code, translation.get_language())
        except (WhatsAppError, WhatsAppTemporaryError) as exc:
            status = str(exc)
            messages.error(request, status)
        else:
            status = _("Sent code %(code)s, message id %(id)s") % {"code": code, "id": message_id}
            messages.success(request, status)

        config.last_test_at = timezone.now()
        config.last_test_status = status
        config.save(update_fields=["last_test_at", "last_test_status", "updated_at"])
        return response
