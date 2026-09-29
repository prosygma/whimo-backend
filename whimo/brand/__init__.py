"""CamerTrace product identity (overrides the upstream WHIMO defaults).

Fork-owned file: on upstream merges keep OUR values, but add any new
setting EFI introduces. Colours follow the CamerTrace graphic chart
(vert cabosse #0B6B3A as primary-600).
"""

NAME = "CamerTrace"

ADMIN_TITLE = f"{NAME} Admin"
ADMIN_HEADER = NAME  # "CamerTrace Administration" is truncated in the sidebar

# Unfold `COLORS["primary"]`: weights 50..950, any CSS colour (hex, oklch...).
ADMIN_PRIMARY_COLORS: dict[str, str] | None = {
    "50": "#EAF5EE",
    "100": "#D3EBDB",
    "200": "#A8D6B8",
    "300": "#74BC8F",
    "400": "#3F9E66",
    "500": "#168049",
    "600": "#0B6B3A",
    "700": "#0A5A31",
    "800": "#084A29",
    "900": "#073D22",
    "950": "#042414",
}

# Static paths (relative to STATIC_URL), e.g. "brand/logo.svg".
ADMIN_LOGO: str | None = None  # sidebar header, light theme (too small for the seal: icon + title instead)
ADMIN_LOGO_DARK: str | None = None  # sidebar header, dark theme (defaults to ADMIN_LOGO)
ADMIN_ICON: str | None = "brand/icon.svg"  # square icon next to the header
ADMIN_FAVICON: str | None = "brand/favicon-32.png"
ADMIN_LOGIN_IMAGE: str | None = "brand/login.webp"  # illustration beside the login form
ADMIN_STYLESHEETS: tuple[str, ...] = ("brand/admin.css",)  # extra CSS, e.g. web fonts
