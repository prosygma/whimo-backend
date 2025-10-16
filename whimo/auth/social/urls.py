from django.urls import path

from whimo.auth.social.views import AppleLoginView, AppleWebLoginView, GoogleLoginView, GoogleWebLoginView

urlpatterns = [
    path("google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("apple/login/", AppleLoginView.as_view(), name="apple_login"),
    path("google/web/login/", GoogleWebLoginView.as_view(), name="google_web_login"),
    path("apple/web/login/", AppleWebLoginView.as_view(), name="apple_web_login"),
]
