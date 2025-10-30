from django.urls import path

from whimo.auth.jwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("", TokenObtainPairView.as_view(), name="token_pair_obtain"),
    path("refresh/", TokenRefreshView.as_view(), name="token_pair_refresh"),
]
