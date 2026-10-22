from django.urls import path

from . import views

app_name = "substitutions"

urlpatterns = [
    path("", views.substitution_list, name="list"),
    path("usulkan/<int:source_pk>/", views.substitution_create, name="create"),
    path("<int:pk>/", views.substitution_detail, name="detail"),
]
