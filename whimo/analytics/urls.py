from django.urls import path

from whimo.analytics.views import AnalyticsView, UserAnalyticsView

urlpatterns = [
    path("", AnalyticsView.as_view(), name="analytics"),
    path("user/", UserAnalyticsView.as_view(), name="user_analytics"),
]
