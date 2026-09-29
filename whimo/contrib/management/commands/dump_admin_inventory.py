"""Dump every registered admin page to JSON so the Playwright suite can prove full coverage.

Test-only helper: the e2e suite reads the output to enumerate the admin surface
independently of link crawling, then asserts the crawl reached all of it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.contrib import admin
from django.core.management.base import BaseCommand
from django.urls import NoReverseMatch, reverse

DEFAULT_OUTPUT = Path("tests/e2e/admin/.data/admin-inventory.json")
SAMPLE_PKS = 3


def _filter_name(entry: Any) -> str:
    if isinstance(entry, (list, tuple)) and entry:
        return str(entry[0])
    if isinstance(entry, str):
        return entry
    return getattr(entry, "parameter_name", None) or getattr(entry, "__name__", str(entry))


def _safe(method: Any, *args: Any, default: Any) -> Any:
    """Admin hooks can raise on stand-in models; the inventory must still be written."""
    try:
        return method(*args)
    except Exception:
        return default


def _reverse(name: str, *args: Any) -> str | None:
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return None


class Command(BaseCommand):
    help = "Write a JSON inventory of every registered Django admin page."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--output", default=str(DEFAULT_OUTPUT))

    def handle(self, *_: Any, **options: Any) -> None:
        request = _FakeRequest()
        models: list[dict] = []

        for model, model_admin in admin.site._registry.items():
            meta = model._meta
            prefix = f"admin:{meta.app_label}_{meta.model_name}"

            # constance registers a stand-in `Config` whose _meta is a hand-rolled
            # stub, not a real Options object, so most attributes are absent.
            verbose_name = str(getattr(meta, "verbose_name", meta.model_name))
            label = getattr(meta, "label", f"{meta.app_label}.{meta.object_name}")

            try:
                pks = [str(pk) for pk in model.objects.values_list("pk", flat=True)[:SAMPLE_PKS]]
                count = model.objects.count()
            except Exception as exc:  # inventory must never hard-fail
                pks, count = [], -1
                self.stderr.write(f"{label}: could not read rows ({exc})")

            models.append(
                {
                    "app_label": meta.app_label,
                    "model_name": meta.model_name,
                    "label": label,
                    "verbose_name": verbose_name,
                    "admin_class": type(model_admin).__name__,
                    "count": count,
                    "sample_pks": pks,
                    "urls": {
                        "changelist": _reverse(f"{prefix}_changelist"),
                        "add": _reverse(f"{prefix}_add"),
                        "change": _reverse(f"{prefix}_change", pks[0]) if pks else None,
                        "history": _reverse(f"{prefix}_history", pks[0]) if pks else None,
                        "delete": _reverse(f"{prefix}_delete", pks[0]) if pks else None,
                        "autocomplete": _reverse("admin:autocomplete"),
                    },
                    "permissions": {
                        "add": _safe(model_admin.has_add_permission, request, default=False),
                        "change": _safe(model_admin.has_change_permission, request, default=False),
                        "delete": _safe(model_admin.has_delete_permission, request, default=False),
                        "view": _safe(model_admin.has_view_permission, request, default=True),
                    },
                    "search_fields": list(model_admin.search_fields or ()),
                    "list_filter": [_filter_name(entry) for entry in (model_admin.list_filter or ())],
                    "list_display": [str(entry) for entry in (model_admin.list_display or ())],
                    "list_filter_submit": bool(getattr(model_admin, "list_filter_submit", False)),
                    "autocomplete_fields": list(getattr(model_admin, "autocomplete_fields", ()) or ()),
                    "readonly_fields": [str(entry) for entry in (model_admin.readonly_fields or ())],
                    "inlines": [type(inline).__name__ for inline in (model_admin.inlines or ())],
                    "actions_detail": list(getattr(model_admin, "actions_detail", ()) or ()),
                    "actions_row": list(getattr(model_admin, "actions_row", ()) or ()),
                    "changelist_actions": sorted(_safe(model_admin.get_actions, request, default={})),
                }
            )

        models.sort(key=lambda entry: entry["label"])

        payload = {
            "admin_index": _reverse("admin:index"),
            "login": _reverse("admin:login"),
            "logout": _reverse("admin:logout"),
            "password_change": _reverse("admin:password_change"),
            "jsi18n": _reverse("admin:jsi18n"),
            "app_list": sorted({entry["app_label"] for entry in models}),
            "models": models,
        }

        output = Path(options["output"])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")

        self.stdout.write(f"Wrote {len(models)} admin models to {output}")


class _FakeRequest:
    """Minimal superuser request: admin permission hooks only touch `.user` and `.GET`."""

    GET: dict = {}
    method = "GET"

    class _User:
        is_active = True
        is_staff = True
        is_superuser = True
        is_authenticated = True

        def has_perm(self, *_: Any, **__: Any) -> bool:
            return True

        def has_perms(self, *_: Any, **__: Any) -> bool:
            return True

        def has_module_perms(self, *_: Any, **__: Any) -> bool:
            return True

    user = _User()
