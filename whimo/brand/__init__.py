"""Product identity: the only module a white-label deployment needs to change.

Settings, the admin (Unfold) and user-facing messages read their name, colours
and logos from here. Defaults are the WHIMO ones; `None` keeps Unfold's own
default. Static files referenced below live in whimo/brand/static/brand/.
"""

NAME = "WHIMO"

ADMIN_TITLE = f"{NAME} Admin"
ADMIN_HEADER = f"{NAME} Administration"

# Unfold `COLORS["primary"]`: weights 50..950, any CSS colour (hex, oklch...).
ADMIN_PRIMARY_COLORS: dict[str, str] | None = None

# Static paths (relative to STATIC_URL), e.g. "brand/logo.svg".
ADMIN_LOGO: str | None = None  # sidebar header, light theme
ADMIN_LOGO_DARK: str | None = None  # sidebar header, dark theme (defaults to ADMIN_LOGO)
ADMIN_ICON: str | None = None  # square icon next to the header
ADMIN_FAVICON: str | None = None
ADMIN_LOGIN_IMAGE: str | None = None  # illustration beside the login form
ADMIN_STYLESHEETS: tuple[str, ...] = ()  # extra CSS, e.g. web fonts
