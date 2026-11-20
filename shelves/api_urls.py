from django.urls import path

from shelves import api_views

app_name = "shelves_api"

urlpatterns = [
    path("", api_views.shelf_list, name="list"),
]
