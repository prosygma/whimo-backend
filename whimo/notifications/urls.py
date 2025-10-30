from django.urls import path

from whimo.notifications.views import (
    NotificationDetailView,
    NotificationDevicesView,
    NotificationSettingsView,
    NotificationsListView,
    NotificationStatusUpdateView,
)

urlpatterns = [
    path("", NotificationsListView.as_view(), name="notifications_list"),
    path("<uuid:notification_id>/", NotificationDetailView.as_view(), name="notification_detail"),
    path("<uuid:notification_id>/status/", NotificationStatusUpdateView.as_view(), name="notification_status_update"),
    path("settings/", NotificationSettingsView.as_view(), name="notification_settings"),
    path("devices/", NotificationDevicesView.as_view(), name="notification_devices"),
]
