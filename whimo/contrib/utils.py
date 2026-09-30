from __future__ import annotations

import hashlib
import json
from typing import Any, Sequence, Type

from django import forms
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString
from unfold.widgets import INPUT_CLASSES, SELECT_CLASSES

from whimo.db.models import BaseModel


class ReadOnlyAdminMixin:
    def has_add_permission(self, _: WSGIRequest, __: Any | None = None) -> bool:
        return False

    def has_delete_permission(self, _: WSGIRequest, __: Any | None = None) -> bool:
        return False

    def has_change_permission(self, _: WSGIRequest, __: Any | None = None) -> bool:
        return False


def name_variant_languages(variants: dict[str, Any]) -> list[tuple[str, str]]:
    """Languages offered for commodity names: those of the admin's Languages page, keyed like
    Django's active language (fr-FR), plus any key already used so that it is never changed."""
    from whimo.languages.models import Language
    from whimo.languages.services import django_code

    choices = [
        (django_code(language.code), language.english_name or language.name) for language in Language.objects.all()
    ]
    if not choices:
        choices = [(code, str(label)) for code, label in settings.LANGUAGES]
    known = {code for code, _label in choices}
    choices += [(code, code) for code in variants if code not in known]
    return choices


class NameVariantsWidget(forms.Widget):
    template_name = "admin/widgets/name_variants.html"

    def get_context(self, name: str, value: Any, attrs: dict | None) -> dict:
        context = super().get_context(name, value, attrs)

        variants = value
        if isinstance(variants, str):
            try:
                variants = json.loads(variants)
            except ValueError:
                variants = {}
        if not isinstance(variants, dict):
            variants = {}

        context["widget"]["rows"] = list(variants.items())
        context["widget"]["languages"] = name_variant_languages(variants)
        context["widget"]["input_class"] = " ".join(INPUT_CLASSES)
        context["widget"]["select_class"] = " ".join(SELECT_CLASSES)
        return context

    def value_from_datadict(self, data: Any, _files: Any, name: str) -> str:
        languages = data.getlist(f"{name}_language")
        values = data.getlist(f"{name}_value")
        variants = {
            language: value.strip()
            for language, value in zip(languages, values, strict=False)
            if language and value.strip()
        }
        return json.dumps(variants)


def get_admin_url(
    model: Type[Model] | Model,
    page_code: str = "change",
    args: Sequence[Any] | None = None,
    kwargs: dict | None = None,
) -> str:
    """Returns reversed admin path.

    Reasoning
    ---------
    - To simplify reverse of admin URLs when you have many models and applications it may be a
        little hard to keep them all in mind to write URL names
    - To encourage people to use the same pattern for URL name when adding new URL to ModelAdmin
    - A little cheatsheet for existing admin URLs bellow


    Cheatsheet
    ----------
    Page	            URL name	                        Parameters
    - Changelist	{app_label}_{model_name}_changelist
    - Add	        {app_label}_{model_name}_add
    - History	    {app_label}_{model_name}_history	    object_id
    - Delete	    {app_label}_{model_name}_delete	        object_id
    - Change	    {app_label}_{model_name}_change	        object_id

    Examples
    --------
    change page of a model:
        get_admin_url(model_instance, args=(model_instance.pk,))

    change list of a model:
        get_admin_url(model_instance, "changelist")

    custom url in ModelAdmin:
        get_admin_url(model_instance, "reindex" args=(model_instance.pk,))

    without model instance:
        get_admin_url(ModelClass, "changelist")

    :param model: Django model class or model instance
    :param page_code: Unique page name that comes after {app_label}_{model_name}_ prefix
    :param args: args to pass to reverse function
    :param kwargs: kwargs to pass to reverse function
    :param lazy: Whether to use lazy version of reverse
    """
    url_name = f"admin:{model._meta.app_label}_{model._meta.model_name}_{page_code}"
    return reverse(url_name, args=args, kwargs=kwargs)


def view_link(url: str, body: Any, new_window: bool = False) -> SafeString:
    target = ' target="_blank"' if new_window else ""
    return format_html('<a class="viewlink" href="{}"{}>{}</a>', url, target, str(body))


def string_to_hex_color(string: str) -> str:
    hash_raw = hashlib.md5(string.encode("utf-8"))
    r, g, b = [hash_raw.digest()[i] for i in range(3)]

    # Make pastel
    r = min(max((r + 0xFF) // 2, 0x8F), 0xFF)
    g = min(max((g + 0xFF) // 2, 0x8F), 0xFF)
    b = min(max((b + 0xFF) // 2, 0x8F), 0xFF)

    return f"#{r:02X}{g:02X}{b:02X}"


def colored_text(text: str, color: str | None = None) -> SafeString:
    if color is None:
        color = string_to_hex_color(text)

    style = format_html("border-radius: 5px; padding: 4px 8px; color: #000; background: {color};", color=color)
    return format_html('<span style="{style}"><b>{text}</b></span>', style=style, text=text)


def text_with_icon(text: str, icon: str) -> SafeString:
    template = '<span class="material-symbols-outlined align-middle">{icon}</span> <b class="align-middle">{text}</b>'
    return format_html(template, icon=icon, text=text)


def change_link_with_icon(obj: Model | None, text: str | None = None, new_window: bool = False) -> SafeString | None:
    if not obj:
        return None

    if text:
        display_text = text
    elif isinstance(obj, BaseModel):
        display_text = colored_text(obj.short_id)
    else:
        display_text = colored_text(str(obj))

    body = text_with_icon(text=display_text, icon="link")
    url = get_admin_url(obj, "change", args=(obj.pk,))
    return view_link(url, body, new_window=new_window)
