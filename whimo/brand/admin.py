"""Turns the values of whimo.brand into Unfold settings."""

from typing import Any

from django.templatetags.static import static

from whimo import brand


def _static(path: str) -> Any:
    # Unfold calls these with the request; resolve lazily so STATIC_URL is final.
    return lambda request: static(path)


def unfold_brand_settings() -> dict[str, Any]:
    config: dict[str, Any] = {
        "SITE_TITLE": brand.ADMIN_TITLE,
        "SITE_HEADER": brand.ADMIN_HEADER,
    }
    if brand.ADMIN_PRIMARY_COLORS:
        config["COLORS"] = {"primary": brand.ADMIN_PRIMARY_COLORS}
    if brand.ADMIN_LOGO:
        config["SITE_LOGO"] = {
            "light": _static(brand.ADMIN_LOGO),
            "dark": _static(brand.ADMIN_LOGO_DARK or brand.ADMIN_LOGO),
        }
    if brand.ADMIN_ICON:
        config["SITE_ICON"] = {"light": _static(brand.ADMIN_ICON), "dark": _static(brand.ADMIN_ICON)}
    if brand.ADMIN_FAVICON:
        config["SITE_FAVICONS"] = [{"rel": "icon", "sizes": "32x32", "href": _static(brand.ADMIN_FAVICON)}]
    if brand.ADMIN_LOGIN_IMAGE:
        config["LOGIN"] = {"image": _static(brand.ADMIN_LOGIN_IMAGE)}
    if brand.ADMIN_STYLESHEETS:
        config["STYLES"] = [_static(path) for path in brand.ADMIN_STYLESHEETS]
    return config
