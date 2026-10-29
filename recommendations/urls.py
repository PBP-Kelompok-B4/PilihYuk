from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.recommendation_list, name="list"),
    path("usulkan/<int:source_pk>/", views.recommendation_create, name="create"),
    path("<int:pk>/edit/", views.recommendation_edit, name="edit"),
    path("<int:pk>/delete/", views.recommendation_delete, name="delete"),
    path("<int:pk>/vote/", views.recommendation_vote, name="vote"),
    path("<int:pk>/", views.recommendation_detail, name="detail"),
]
