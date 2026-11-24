"""URL API Modul Antrean Data di /api/v1/corrections/."""
from django.urls import path

from data_correction import api_views

app_name = "data_correction_api"

urlpatterns = [
    path("queue/", api_views.contribution_queue, name="contribution_queue"),
    path("products/<int:pk>/form/", api_views.correction_form, name="correction_form"),
    path("mine/", api_views.my_corrections, name="my_corrections"),
    path("mine/<int:pk>/", api_views.correction_detail, name="correction_detail"),
]