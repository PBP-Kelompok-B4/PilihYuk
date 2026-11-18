"""URL API Modul Antrean Data, dimuat di /api/v1/corrections/ oleh pilihyuk/urls.py.
"""
from django.urls import path

from data_correction import api_views

app_name = "data_correction_api"

urlpatterns = [
    path("queue/", api_views.contribution_queue, name="contribution_queue"),
]