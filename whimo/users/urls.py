from django.urls import path

from whimo.users.views import GadgetExistsView, GadgetView, ProfilePasswordChangeView, ProfileView

urlpatterns = [
    path("gadgets/exists/", GadgetExistsView.as_view(), name="gadgets_exists"),
    path("gadgets/", GadgetView.as_view(), name="gadgets"),
    path("profile/", ProfileView.as_view(), name="users_profile"),
    path("profile/password/", ProfilePasswordChangeView.as_view(), name="users_profile_password_change"),
]
