from django.contrib import admin
from django.urls import include, path

auth_urlpatterns = [
    path("auth/jwt/", include("whimo.auth.jwt.urls")),
    path("auth/otp/", include("whimo.auth.otp.urls")),
    path("auth/registration/", include("whimo.auth.registration.urls")),
    path("auth/social/", include("whimo.auth.social.urls")),
]

data_urlpatterns = [
    path("analytics/", include("whimo.analytics.urls")),
    path("commodities/", include("whimo.commodities.urls")),
    path("harvest-seasons/", include("whimo.harvest_seasons.urls")),
    path("languages/", include("whimo.languages.urls")),
    path("system/", include("whimo.system.urls")),
    path("notifications/", include("whimo.notifications.urls")),
    path("transactions/", include("whimo.transactions.urls")),
    path("users/", include("whimo.users.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(auth_urlpatterns + data_urlpatterns)),
    # Test mode: the same data endpoints, isolated in the test_mode schema (see
    # whimo.common.middleware.TestModeMiddleware and whimo.common.db_router). Auth
    # is deliberately not mounted here - logging in always happens against public.
    # Namespaced so reverse("transactions_list") keeps resolving the normal route -
    # without a namespace, reusing the same names here would make it ambiguous.
    path("api/v1/test/", include((data_urlpatterns, "test_mode"), namespace="test_mode")),
]
