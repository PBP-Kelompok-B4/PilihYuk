"""Konstanta Modul 4 (Antrean Data).

Notes:
- File ini adalah "buku aturan" modul Antrean Data. Semua daftar dan nama tetap
  dikumpulkan di sini, lalu dipakai bersama oleh models.py, checks.py, forms.py,
  validasi, template, dan tes. Kalau perlu mengubah aturan, cukup ubah di satu tempat ini
- Satu-satunya sumber daftar field Product yang boleh dikoreksi (PRD F-4.2)
- Sengaja TIDAK mengimpor model apa pun, supaya file mana saja bisa mengimpornya
  tanpa risiko circular import
- Kecocokan daftar ini dengan model Product diperiksa otomatis oleh system check
  di checks.py (didaftarkan di apps.py). Kalau nama kolom Product berubah,
  `python manage.py check` langsung memberi error
"""

# Urutan mengikuti PRD F-4.2
CORRECTABLE_FIELDS = (
    "product_name",
    "brand",
    "quantity",
    "category",
    "origin",
    "nova_group",
    "energy_kcal_100g",
    "proteins_100g",
    "fat_100g",
    "saturated_fat_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "fiber_100g",
    "sodium_100g",
)

# TextField NOT NULL: nilai kosong berupa "" dan panjangnya dibatasi max_length kolom
TEXT_FIELDS = ("product_name", "brand", "quantity", "category", "origin")

# IntegerField 1 sampai 4, boleh NULL
INTEGER_FIELDS = ("nova_group",)

# FloatField per 100 g, boleh NULL, nilainya harus >= 0. Nilai 0 sah, bukan kosong
NUTRITION_FIELDS = (
    "energy_kcal_100g",
    "proteins_100g",
    "fat_100g",
    "saturated_fat_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "fiber_100g",
    "sodium_100g",
)

# Label antarmuka. Satuan mengikuti kolom Product (energi dalam kkal, gizi lain dalam
# gram), kecuali natrium: kolomnya gram, tetapi pengguna mengisi dan membaca miligram
# seperti di halaman katalog (keputusan 1 setelah Tahap 0). Lihat DISPLAY_FACTORS.
FIELD_LABELS = {
    "product_name": "Nama produk",
    "brand": "Merek",
    "quantity": "Berat / isi bersih",
    "category": "Kategori",
    "origin": "Asal produk",
    "nova_group": "Grup NOVA",
    "energy_kcal_100g": "Energi (kkal/100 g)",
    "proteins_100g": "Protein (g/100 g)",
    "fat_100g": "Lemak (g/100 g)",
    "saturated_fat_100g": "Lemak jenuh (g/100 g)",
    "carbohydrates_100g": "Karbohidrat (g/100 g)",
    "sugars_100g": "Gula (g/100 g)",
    "fiber_100g": "Serat (g/100 g)",
    "sodium_100g": "Natrium (mg/100 g)",
}

# Nilai di antarmuka = nilai kolom x faktor. Input pengguna dibagi faktor saat validasi,
# jadi old_value dan proposed_value selalu tersimpan dalam satuan kolom (gram) dan
# persetujuan cukup menulis nilainya ke Product.
DISPLAY_FACTORS = {"sodium_100g": 1000}

FIELD_CHOICES = tuple((name, FIELD_LABELS[name]) for name in CORRECTABLE_FIELDS)

# Status DataCorrectionItem.
PENDING = "pending"
APPROVED = "approved"
REJECTED = "rejected"
STATUS_CHOICES = (
    (PENDING, "Menunggu"),
    (APPROVED, "Disetujui"),
    (REJECTED, "Ditolak"),
)

# Status DataCorrection tidak disimpan, melainkan diturunkan dari item (PRD bagian 7).
# PARTIAL hanya ada di tingkat pengajuan: tidak ada item pending dan hasilnya campuran.
PARTIAL = "partial"
CORRECTION_STATUS_LABELS = {
    PENDING: "Menunggu",
    APPROVED: "Disetujui",
    REJECTED: "Ditolak",
    PARTIAL: "Sebagian disetujui",
}