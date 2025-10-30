from django.contrib import admin
from django.urls import include, path

api_v1_urlpatterns = [
    path("analytics/", include("whimo.analytics.urls")),
    path("auth/jwt/", include("whimo.auth.jwt.urls")),
    path("auth/otp/", include("whimo.auth.otp.urls")),
    path("auth/registration/", include("whimo.auth.registration.urls")),
    path("auth/social/", include("whimo.auth.social.urls")),
    path("commodities/", include("whimo.commodities.urls")),
    path("system/", include("whimo.system.urls")),
    path("notifications/", include("whimo.notifications.urls")),
    path("transactions/", include("whimo.transactions.urls")),
    path("users/", include("whimo.users.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_urlpatterns)),
]
