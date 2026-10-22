from django.urls import path

from . import views

app_name = "data_correction"

urlpatterns = [
    path("antrean/produk/<int:pk>/ajukan/", views.submit, name="submit"),
    path("antrean/saya/", views.my_corrections, name="my_corrections"),
    path("antrean/saya/<int:pk>/", views.correction_detail, name="correction_detail"),
    path("antrean/saya/<int:pk>/tarik/", views.withdraw, name="withdraw"),
]