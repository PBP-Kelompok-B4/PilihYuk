from django.urls import path

from . import views

app_name = "shelves"

urlpatterns = [
    path("", views.shelf_list, name="list"),
    path("saya/", views.shelf_mine, name="mine"),
    path("buat/", views.shelf_create, name="create"),
    path("<int:pk>/", views.shelf_detail, name="detail"),
    path("<int:pk>/ubah/", views.shelf_edit, name="edit"),
    path("<int:pk>/hapus/", views.shelf_delete, name="delete"),
    path("<int:pk>/kandidat/", views.shelf_candidates, name="candidates"),
    path("<int:pk>/produk/", views.shelf_item_add, name="item_add"),
    path("<int:pk>/produk/<int:product_id>/hapus/", views.shelf_item_remove, name="item_remove"),
]
