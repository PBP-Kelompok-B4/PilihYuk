from django.urls import path

from . import views

app_name = "product_catalog"

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("lookup/", views.product_lookup, name="product_lookup"),
    path("tambah-manual/", views.product_add_manual, name="product_add_manual"),
    path("riwayat/", views.product_history, name="product_history"),
    path("<int:pk>/sunting/", views.product_edit, name="product_edit"),
    path("<int:pk>/hapus/", views.product_delete, name="product_delete"),
    path("<int:pk>/", views.product_detail, name="product_detail"),
]
