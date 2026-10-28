"""System check: daftar field di constants.py harus cocok dengan model Product

CATATAN:
- Apa itu system check? Pemeriksaan otomatis bawaan Django yang berjalan setiap kali
  menjalankan `manage.py check`, `runserver`, `migrate`, dan `test`. Kalau check
  mengembalikan Error, perintah itu langsung berhenti dan menampilkan pesannya
- Kenapa perlu? Saat kurator menyetujui koreksi, nilai ditulis ke Product dengan
  setattr(product, field_name, nilai). Kalau field_name tidak ada di model (misalnya
  kolom Product diganti nama oleh pemilik modul Katalog), setattr TIDAK memberi error:
  nilainya hanya menempel di objek Python dan tidak pernah tersimpan ke database.
  Kesalahan seperti ini diam-diam dan sulit dilacak. Check ini menangkapnya lebih awal.
- Kenapa system check, bukan tes saja? Tes hanya berjalan saat `manage.py test`.
  System check ikut berjalan di runserver dan migrate juga, jadi masalahnya langsung
  terlihat.
- Konsekuensi: kalau constants.py dan Product tidak cocok, migrate seluruh proyek ikut
  berhenti (termasuk saat deploy di PWS). Ini disengaja ("gagal keras").
- Check ini didaftarkan di apps.py (method ready). Tanpa pendaftaran itu, file ini
  tidak pernah dijalankan.
- Model Product diambil lewat apps.get_model saat check berjalan (registry app sudah
  siap), bukan diimpor di bagian atas file, agar tidak memicu circular import.

Kode error yang bisa muncul:
- data_correction.E001: isi constants.py tidak konsisten dengan dirinya sendiri.
- data_correction.E002: model product_catalog.Product tidak ditemukan.
- data_correction.E003: ada field di CORRECTABLE_FIELDS yang tidak ada di Product.
- data_correction.E004: tipe kolom Product tidak sesuai kelompoknya di constants.py.
"""

from django.apps import apps
from django.core import checks
from django.core.exceptions import FieldDoesNotExist
from django.db import models

from . import constants

APP_LABEL = "data_correction"
SOURCE = "data_correction.constants"

# Tipe kolom yang diandalkan validasi dan konversi nilai di modul ini.
EXPECTED_TYPES = (
    ("TEXT_FIELDS", models.CharField),
    ("INTEGER_FIELDS", models.IntegerField),
    ("NUTRITION_FIELDS", models.FloatField),
)


def check_correctable_fields(app_configs=None, **kwargs):
    if app_configs is not None and not any(config.label == APP_LABEL for config in app_configs):
        return []
    errors = check_constants()
    try:
        product_model = apps.get_model("product_catalog", "Product")
    except LookupError:
        errors.append(checks.Error(
            "Model product_catalog.Product tidak ditemukan.",
            hint="Modul Antrean Data membutuhkan app product_catalog di INSTALLED_APPS.",
            obj=SOURCE,
            id="data_correction.E002",
        ))
        return errors
    for group_name, field_class in EXPECTED_TYPES:
        for name in getattr(constants, group_name):
            try:
                field = product_model._meta.get_field(name)
            except FieldDoesNotExist:
                errors.append(checks.Error(
                    f"Field '{name}' di CORRECTABLE_FIELDS tidak ada di model Product.",
                    hint="Samakan data_correction/constants.py dengan product_catalog/models.py.",
                    obj=SOURCE,
                    id="data_correction.E003",
                ))
                continue
            if not isinstance(field, field_class):
                errors.append(checks.Error(
                    f"Product.{name} bertipe {type(field).__name__}, padahal {group_name} "
                    f"mengharapkan {field_class.__name__}.",
                    hint="Pindahkan field ke kelompok yang sesuai di constants.py dan sesuaikan validasinya.",
                    obj=SOURCE,
                    id="data_correction.E004",
                ))
    return errors


def check_constants():
    """Konsistensi internal constants.py, tanpa menyentuh model."""
    errors = []
    fields = constants.CORRECTABLE_FIELDS
    grouped = constants.TEXT_FIELDS + constants.INTEGER_FIELDS + constants.NUTRITION_FIELDS
    if len(set(fields)) != len(fields) or sorted(grouped) != sorted(fields):
        errors.append(checks.Error(
            "TEXT_FIELDS, INTEGER_FIELDS, dan NUTRITION_FIELDS harus membagi CORRECTABLE_FIELDS "
            "tanpa duplikat dan tanpa sisa.",
            obj=SOURCE,
            id="data_correction.E001",
        ))
    if set(constants.FIELD_LABELS) != set(fields):
        errors.append(checks.Error(
            "FIELD_LABELS harus memuat label untuk tepat setiap field di CORRECTABLE_FIELDS.",
            obj=SOURCE,
            id="data_correction.E001",
        ))
    if not set(constants.DISPLAY_FACTORS) <= set(constants.NUTRITION_FIELDS):
        errors.append(checks.Error(
            "DISPLAY_FACTORS hanya boleh berisi field dari NUTRITION_FIELDS.",
            obj=SOURCE,
            id="data_correction.E001",
        ))
    return errors