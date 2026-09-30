import json
from typing import Any

from django import forms
from django.contrib import admin, messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.html import format_html_join
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.decorators import action, display
from unfold.widgets import UnfoldAdminFileFieldWidget

from whimo.contrib.utils import get_admin_url
from whimo.languages import catalog
from whimo.languages.models import Language


class LanguageForm(forms.ModelForm):
    translations_file = forms.FileField(
        label=_("Translations file"),
        required=False,
        widget=UnfoldAdminFileFieldWidget,
        help_text=_(
            "JSON file with the strings of this language. To start, use “Download English template”, "
            "translate the values (keep the keys and the placeholders such as %s, %@ or {{count}}), then "
            "upload it here. To correct a few strings, use “Download translations” on this language, "
            "change them and upload the file again. Strings left in English are ignored."
        ),
    )

    class Meta:
        model = Language
        fields = ("code", "name", "english_name", "flag", "is_enabled", "is_default", "position")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.upload: catalog.UploadResult | None = None
        if not self.instance._state.adding:
            # The code keys the uploaded strings and the apps' saved choice: keep it.
            self.fields["code"].disabled = True

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        file = cleaned.get("translations_file")
        code = cleaned.get("code") or self.instance.code
        if file and code:
            upload = catalog.parse_upload(code, file.read(), previous=self.instance.translations or {})
            if upload.is_valid:
                self.upload = upload
            else:
                shown = upload.errors[:20]
                more = len(upload.errors) - len(shown)
                errors = [*shown, _("…and %d more errors.") % more] if more > 0 else shown
                self.add_error("translations_file", errors)
        return cleaned


@admin.register(Language)
class LanguageAdmin(ModelAdmin):
    form = LanguageForm
    list_display = ("display_name", "code", "is_enabled", "is_default", "position", "completion", "version")
    list_editable = ("is_enabled", "position")
    list_display_links = ("display_name",)
    search_fields = ("code", "name", "english_name")
    readonly_fields = ("completion", "uploaded_strings", "version", "id", "created_at", "updated_at")
    actions_list = ("download_template",)  # type: ignore
    actions_detail = ("download_translations", "make_default")  # type: ignore

    fieldsets = (
        (None, {"fields": ("code", "name", "english_name", "flag")}),
        (_("Availability"), {"fields": ("is_enabled", "is_default", "position")}),
        (_("Translations"), {"fields": ("translations_file", "completion", "uploaded_strings", "version")}),
        (_("Metadata"), {"fields": ("id", "created_at", "updated_at")}),
    )

    @display(description=_("Language"))
    def display_name(self, obj: Language) -> str:
        return f"{obj.flag} {obj.name}".strip()

    @display(description=_("Translated"))
    def completion(self, obj: Language) -> str:
        total = catalog.template_size()
        if not obj.code or not total:
            return "-"
        done = catalog.translated_count(obj.code, obj.translations or {})
        return f"{done} / {total} ({round(100 * done / total)}%)"

    @display(description=_("Uploaded strings"))
    def uploaded_strings(self, obj: Language) -> str:
        pack = obj.translations or {}
        counts = [(platform, sum(1 for _ in catalog.iter_strings(pack, platform))) for platform in catalog.PLATFORMS]
        if not any(count for _, count in counts):
            return str(_("None: the apps show their own strings."))
        return format_html_join(", ", "{}: {}", counts)

    def has_delete_permission(self, request: HttpRequest, obj: Language | None = None) -> bool:
        return super().has_delete_permission(request, obj) and not (obj and obj.is_default)

    def save_model(self, request: HttpRequest, obj: Any, form: Any, change: bool) -> None:
        upload: catalog.UploadResult | None = getattr(form, "upload", None)
        if upload is not None:
            obj.translations = upload.translations
            obj.version = (obj.version or 0) + 1
        super().save_model(request, obj, form, change)
        if upload is not None:
            messages.success(
                request,
                _("%(stored)d strings stored, %(unchanged)d left as the apps already show them.")
                % {"stored": upload.stored, "unchanged": upload.unchanged},
            )

    @action(description=_("Download English template"), url_path="download-template", icon="download")
    def download_template(self, _: HttpRequest) -> HttpResponse:
        return json_attachment(catalog.download(catalog.TEMPLATE_CODE, {}), "translations-template-en.json")

    @action(description=_("Download translations"), url_path="download", icon="download")
    def download_translations(self, _: HttpRequest, object_id: str) -> HttpResponse:
        language = Language.objects.get(pk=object_id)
        pack = catalog.download(language.code, language.translations or {})
        return json_attachment(pack, f"translations-{language.code}.json")

    @action(description=_("Make default"), url_path="make-default", icon="star")
    def make_default(self, request: HttpRequest, object_id: str) -> HttpResponse:
        language = Language.objects.get(pk=object_id)
        if not language.is_enabled:
            messages.error(request, _("Enable the language before making it the default one."))
        else:
            language.is_default = True
            language.save()
            messages.success(request, _("%s is now the default language.") % language.name)
        return redirect(get_admin_url(Language, "change", args=(object_id,)))


def json_attachment(data: dict, filename: str) -> HttpResponse:
    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    response = HttpResponse(content, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
