from datetime import timedelta
from pathlib import Path

import environ
import firebase_admin
import sentry_sdk
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

env = environ.Env()

_not_set = object()

# Django
# ______________________________________________________________________________________________________________________

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env.str("DJANGO_SECRET_KEY")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=())

CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=())

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=())

INSTALLED_APPS = (
    # unfold admin
    "unfold",
    "unfold.contrib.simple_history",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "unfold.contrib.import_export",
    # django core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.humanize",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party apps
    "constance",
    "corsheaders",
    "import_export",
    "rest_framework",
    "rest_framework_simplejwt",
    "simple_history",
    "django_celery_beat",
    "django_celery_results",
    "push_notifications",
    # project apps
    "whimo.db",
    "whimo.analytics",
    "whimo.auth.jwt",
    "whimo.auth.otp",
    "whimo.auth.registration",
    "whimo.auth.social",
    "whimo.commodities",
    "whimo.common",
    "whimo.contrib",
    "whimo.notifications",
    "whimo.system",
    "whimo.transactions",
    "whimo.users",
)

MIDDLEWARE = (
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
)

ROOT_URLCONF = "whimo.urls"

TEMPLATES = (
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": (BASE_DIR / "whimo" / "contrib" / "templates",),
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": (
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ),
        },
    },
)

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

WSGI_APPLICATION = "whimo.common.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("whimo.common.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("whimo.common.authentication.HasVerifiedGadgetPermission",),
    "DEFAULT_THROTTLE_CLASSES": [
        "whimo.common.throttling.DefaultUserThrottle",
        "whimo.common.throttling.DefaultAnonThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "otp": "5/minute",
        "auth": "20/minute",
        "downloads": "10/hour",
    },
    "EXCEPTION_HANDLER": "whimo.common.views.custom_exception_handler",
}

# Logging
# ______________________________________________________________________________________________________________________

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
            "filters": None,
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
        },
    },
}

# Sentry
# ______________________________________________________________________________________________________________________

SENTRY_DSN = env.str("SENTRY_DSN", default="")

SENTRY_ENVIRONMENT = env.str("SENTRY_ENVIRONMENT", default="production")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    send_default_pii=True,
    environment=SENTRY_ENVIRONMENT,
    traces_sample_rate=1.0,
    profile_session_sample_rate=1.0,
    profile_lifecycle="trace",
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(monitor_beat_tasks=True),
    ],
    _experiments={
        "enable_logs": True,
    },
)

# Databases
# ______________________________________________________________________________________________________________________

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": env.str("POSTGRES_HOST", default="127.0.0.1"),
        "PORT": env.int("POSTGRES_PORT", default=5432),
        "USER": env.str("POSTGRES_USER", default="app"),
        "PASSWORD": env.str("POSTGRES_PASSWORD"),
        "NAME": env.str("POSTGRES_DB", default="app"),
    },
}

# Caching
# ______________________________________________________________________________________________________________________

REDIS_HOST = env.str("REDIS_HOST", default="127.0.0.1")

REDIS_PORT = env.int("REDIS_PORT", default=6379)

REDIS_DB = env.int("REDIS_DB", default=0)

REDIS_PASSWORD = env.str("REDIS_PASSWORD")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "PASSWORD": REDIS_PASSWORD,
        },
    },
}

# Celery
# ----------------------------------------------------------------------------------------------------------------------

CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CELERY_RESULT_BACKEND = "django-db"

CELERY_CACHE_BACKEND = "django-cache"

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Storages
# ______________________________________________________________________________________________________________________

S3_OPTIONS = {
    "endpoint_url": env.str("S3_ENDPOINT_URL", default=_not_set),
    "region_name": env.str("S3_REGION", default=_not_set),
    "bucket_name": env.str("S3_BUCKET_NAME", default=_not_set),
    "access_key": env.str("S3_ACCESS_KEY", default=_not_set),
    "secret_key": env.str("S3_SECRET_KEY", default=_not_set),
}

S3_OPTIONS = {option: value for option, value in S3_OPTIONS.items() if value is not _not_set}

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": S3_OPTIONS,
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Security
# ______________________________________________________________________________________________________________________

OTP_LENGTH = env.int("OTP_LENGTH", default=6)

OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=5)

OTP_MOCK_CODE = env.str("OTP_MOCK_CODE", default=None)

AUTH_USER_MODEL = "db.User"

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "whimo.common.authentication.GadgetsModelBackend",
)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}

AUTH_PASSWORD_VALIDATORS = ()

# Email
# ______________________________________________________________________________________________________________________

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = env.str("EMAIL_HOST", default="localhost")

EMAIL_PORT = env.int("EMAIL_PORT", default=25)

EMAIL_HOST_USER = env.str("EMAIL_HOST_USER", default="whimo")

EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER)

EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# SMS
# ______________________________________________________________________________________________________________________

SMS_GATEWAY_TIMEOUT = env.int("SMS_GATEWAY_TIMEOUT", default=30)

SMS_GATEWAY_DEFAULT_TAG = env.str("SMS_GATEWAY_DEFAULT_TAG", default="GSM")

if env.bool("SMS_GATEWAY_ENABLED", default=False):  # pragma: no cover
    SMS_GATEWAY_PORT = env.str("SMS_GATEWAY_PORT")

    SMS_GATEWAY_BASE_URL = f"http://smsgw.gtsnetwork.cloud:{SMS_GATEWAY_PORT}/message"

    SMS_GATEWAY_USERNAME = env.str("SMS_GATEWAY_USERNAME")

    SMS_GATEWAY_PASSWORD = env.str("SMS_GATEWAY_PASSWORD")

    SMS_GATEWAY_SENDER_ID = env.str("SMS_GATEWAY_SENDER_ID")

# Firebase
# ______________________________________________________________________________________________________________________

PUSH_NOTIFICATIONS_CONFIG_PATH = BASE_DIR / "config" / "push"

PUSH_NOTIFICATIONS_SETTINGS_FCM_APP_ID = env.str("PUSH_NOTIFICATIONS_FCM_APP_ID", default="fcm")

PUSH_NOTIFICATIONS_SETTINGS_APNS_APP_ID = env.str("PUSH_NOTIFICATIONS_APNS_APP_ID", default="apns")

PUSH_NOTIFICATIONS_SETTINGS = {
    "CONFIG": "push_notifications.conf.AppConfig",
    "USER_MODEL": AUTH_USER_MODEL,
    "APPLICATIONS": {},
}

if env.bool("PUSH_NOTIFICATIONS_FCM_ENABLED", default=False):  # pragma: no cover
    PUSH_NOTIFICATIONS_SETTINGS["APPLICATIONS"][PUSH_NOTIFICATIONS_SETTINGS_FCM_APP_ID] = {  # type: ignore
        "PLATFORM": "FCM",
        "FIREBASE_APP": firebase_admin.initialize_app(
            credential=firebase_admin.credentials.Certificate(PUSH_NOTIFICATIONS_CONFIG_PATH / "fcm.json"),
        ),
    }

if env.bool("PUSH_NOTIFICATIONS_APNS_ENABLED", default=False):  # pragma: no cover
    PUSH_NOTIFICATIONS_SETTINGS["APPLICATIONS"][PUSH_NOTIFICATIONS_SETTINGS_APNS_APP_ID] = {  # type: ignore
        "PLATFORM": "APNS",
        "CERTIFICATE": str(PUSH_NOTIFICATIONS_CONFIG_PATH / "apns.pem"),
        "USE_SANDBOX": env.bool("PUSH_NOTIFICATIONS_APNS_USE_SANDBOX", default=False),
    }

# Localization
# ______________________________________________________________________________________________________________________

LANGUAGE_CODE = "en-US"

LANGUAGES = (
    ("en-US", "English"),
    ("fr-FR", "French"),
    ("es-ES", "Spanish"),
)

LOCALE_PATHS = (BASE_DIR / "locale",)

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# Static files
# ______________________________________________________________________________________________________________________

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "static"

# Proxy
# ______________________________________________________________________________________________________________________

USE_X_FORWARDED_HOST = env.bool("DJANGO_USE_X_FORWARDED_HOST", False)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", env.str("DJANGO_HTTP_X_FORWARDED_PROTO", "http"))

# Misc
# ______________________________________________________________________________________________________________________

WHIMO_TRANSACTION_EXPIRATION_DAYS = env.int("WHIMO_TRANSACTION_EXPIRATION_DAYS", default=30)

# Django Admin
# ______________________________________________________________________________________________________________________

UNFOLD = {
    "SITE_TITLE": "WHIMO Admin",
    "SITE_HEADER": "WHIMO Administration",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "whimo.contrib.admin.dashboard.dashboard_callback",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                    {
                        "title": _("Periodic Tasks"),
                        "icon": "task",
                        "link": reverse_lazy("admin:django_celery_beat_periodictask_changelist"),
                    },
                ],
            },
            {
                "title": _("User Management"),
                "separator": True,
                "items": [
                    {
                        "title": _("Users"),
                        "icon": "person",
                        "link": reverse_lazy("admin:db_user_changelist"),
                    },
                    {
                        "title": _("Gadgets"),
                        "icon": "devices",
                        "link": reverse_lazy("admin:db_gadget_changelist"),
                    },
                    {
                        "title": _("Notifications"),
                        "icon": "notifications",
                        "link": reverse_lazy("admin:db_notification_changelist"),
                    },
                ],
            },
            {
                "title": _("Commodities"),
                "separator": True,
                "items": [
                    {
                        "title": _("Commodity Groups"),
                        "icon": "category",
                        "link": reverse_lazy("admin:db_commoditygroup_changelist"),
                    },
                    {
                        "title": _("Commodities"),
                        "icon": "inventory",
                        "link": reverse_lazy("admin:db_commodity_changelist"),
                    },
                    {
                        "title": _("Seasons"),
                        "icon": "calendar_month",
                        "link": reverse_lazy("admin:db_season_changelist"),
                    },
                ],
            },
            {
                "title": _("Trading"),
                "separator": True,
                "items": [
                    {
                        "title": _("Transactions"),
                        "icon": "swap_horiz",
                        "link": reverse_lazy("admin:db_transaction_changelist"),
                    },
                    {
                        "title": _("Balances"),
                        "icon": "account_balance",
                        "link": reverse_lazy("admin:db_balance_changelist"),
                    },
                ],
            },
        ],
    },
}
