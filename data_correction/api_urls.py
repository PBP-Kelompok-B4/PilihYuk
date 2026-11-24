"""URL API Modul Antrean Data, dimuat di /api/v1/corrections/ oleh pilihyuk/urls.py.

Endpoint (nama URL di namespace data_correction_api):
    GET   queue/                 contribution_queue   antrean kontribusi, publik
    GET   products/<pk>/form/    correction_form      field koreksi + nilai saat ini, wajib masuk
    POST  mine/                  my_corrections       ajukan koreksi, wajib masuk + token CSRF
"""
from django.urls import path

from data_correction import api_views

app_name = "data_correction_api"

urlpatterns = [
    path("queue/", api_views.contribution_queue, name="contribution_queue"),
    path("products/<int:pk>/form/", api_views.correction_form, name="correction_form"),
    path("mine/", api_views.my_corrections, name="my_corrections"),
]