from django.urls import path

from whimo.camertrace.views import AppOptionsView

urlpatterns = [
    path("", AppOptionsView.as_view(), name="app_options"),
]
