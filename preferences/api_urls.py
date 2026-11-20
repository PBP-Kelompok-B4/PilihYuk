from django.urls import path

from . import api_views

app_name = "preferences_api"

urlpatterns = [
    path("", api_views.preference_list, name="preference-list"),
    path("<int:pk>/", api_views.preference_detail, name="preference-detail"),
    path("preview/", api_views.preference_preview, name="preference-preview"),
    path("preview/combined/", api_views.preference_combined_preview, name="preference-combined-preview"),
    path("decisions/", api_views.decision_list, name="decision-list"),
    path("decisions/<int:pk>/", api_views.decision_detail, name="decision-detail"),
    path("decisions/bulk-delete/", api_views.decision_bulk_delete, name="decision-bulk-delete"),
]
