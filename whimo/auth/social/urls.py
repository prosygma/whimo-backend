from django.urls import path

from whimo.auth.social.views import AppleLoginView, GoogleLoginView

urlpatterns = [
    path("google/login/", GoogleLoginView.as_view(), name="google_login"),
    path("apple/login/", AppleLoginView.as_view(), name="apple_login"),
]
