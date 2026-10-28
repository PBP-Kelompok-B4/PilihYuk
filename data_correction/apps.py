"""Konfigurasi app data_correction (Modul 4: Antrean Data).

Notes:
- Class yang memberi tahu Django identitas dan pengaturan sebuah app.
  Django membacanya sekali saat proyek dinyalakan (runserver, migrate, test, check).
- App ini sudah terdaftar di INSTALLED_APPS (settings.py) sebagai "data_correction".
  Django otomatis memakai kelas DataCorrectionConfig di bawah karena hanya ada satu
  AppConfig di file ini. Jadi settings.py tidak perlu diubah.
- Tugas tambahan file ini: mendaftarkan system check dari checks.py lewat method ready().
  Tanpa pendaftaran itu, checks.py tidak pernah dijalankan.
"""

from django.apps import AppConfig

class DataCorrectionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField" 
    name = "data_correction"
    verbose_name = "Antrean Data"

    def ready(self):
        # Diimpor di sini, bukan di tingkat modul, agar registry app sudah siap dan tidak
        # ada circular import dengan product_catalog.
        from django.core import checks

        from .checks import check_correctable_fields

        checks.register(check_correctable_fields, checks.Tags.models)