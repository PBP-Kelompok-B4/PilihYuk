from django.urls import path

from . import views

app_name = "preferences"
urlpatterns = [
    path("preferensi/", views.preference_list, name="preference_list"),
    path("preferensi/simpan/", views.preference_save, name="preference_save"),
    path("preferensi/pratinjau-gabungan/", views.preference_combined_preview, name="preference_combined_preview"),
    path("preferensi/pratinjau/", views.preference_preview, name="preference_preview"),
    path("preferensi/tambah/", views.preference_create, name="preference_create"),
    path("preferensi/<int:pk>/ubah/", views.preference_update, name="preference_update"),
    path("preferensi/<int:pk>/hapus/", views.preference_delete, name="preference_delete"),
    path("keputusan/", views.decision_list, name="decision_list"),
    path("keputusan/ekspor/", views.decision_export, name="decision_export"),
    path("keputusan/tambah/", views.decision_create, name="decision_create"),
    path("keputusan/hapus-massal/", views.decision_bulk_delete, name="decision_bulk_delete"),
    path("keputusan/<int:pk>/ubah/", views.decision_update, name="decision_update"),
    path("keputusan/<int:pk>/hapus/", views.decision_delete, name="decision_delete"),
]
