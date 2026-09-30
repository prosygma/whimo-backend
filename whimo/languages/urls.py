from django.urls import path

from whimo.languages.views import LanguagesListView, LanguageStringsView

urlpatterns = [
    path("", LanguagesListView.as_view(), name="languages_list"),
    path("<str:code>/<str:platform>/", LanguageStringsView.as_view(), name="languages_strings"),
]
