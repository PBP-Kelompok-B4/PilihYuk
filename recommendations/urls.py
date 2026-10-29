from django.urls import path

from . import views

app_name = "recommendations"

urlpatterns = [
    path("", views.recommendation_list, name="list"),
    path("usulkan/<int:source_pk>/", views.recommendation_create, name="create"),
    path("<int:pk>/vote/", views.recommendation_vote, name="vote"),
    path("<int:pk>/", views.recommendation_detail, name="detail"),
]
