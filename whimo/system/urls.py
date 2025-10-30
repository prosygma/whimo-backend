from django.urls import path

from whimo.system.views import HealthcheckView

urlpatterns = [
    path("healthcheck/", HealthcheckView.as_view(), name="system_healthcheck"),
]
