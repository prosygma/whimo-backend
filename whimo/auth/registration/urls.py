from django.urls import path

from whimo.auth.registration.views import RegistrationView

urlpatterns = [
    path("", RegistrationView.as_view(), name="registration"),
]
