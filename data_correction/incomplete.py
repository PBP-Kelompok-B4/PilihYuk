"""Deteksi produk yang datanya incomplete, untuk antrean kontribusi (PRD F-4.7).

CATATAN:
- Menentukan produk mana yang masuk "Antrean Kelengkapan Data", dan
  data apa saja yang kurang dari setiap produk (ditampilkan sebagai chip).
- Aturan "belum lengkap" (keputusan 3 setelah Tahap 0). Produk masuk antrean kalau:
  1. misc_tags memuat salah satu dari empat tag contoh PRD, ATAU
  2. ada field koreksi yang kosong: kolom gizi NULL, nova_group NULL, atau
     brand/quantity/origin berupa teks kosong.
- Yang TIDAK dianggap kosong:
  - nilai 0 (mis. serat 0 g itu data yang sah);
  - grade "unknown" saja (kolom grade tidak pernah dibaca di file ini).
- Kenapa diperiksa di Python, bukan lewat query database?
  misc_tags disimpan di JSONField, dan K-3 melarang query isi JSONField (lookup
  `contains` tidak didukung SQLite). Database hanya dipakai untuk mengambil kolom yang
  perlu lewat .values(); pemeriksaannya dilakukan di Python.
- Kondisi data saat ini: misc_tags kosong di 406 dari 406 produk seed (dump CSV tidak
  memuatnya, K-12). Jadi untuk data seed, yang menentukan adalah kolom kosong.
  misc_tags hanya terisi pada produk hasil lookup barcode.
- Bentuk setiap kategori data kurang (satu chip):
      {"key": "nutrition", "label": "Gizi", "correctable": True, "fields": ["fiber_100g"]}
  - correctable=True  : bisa dilengkapi lewat form koreksi; "fields" berisi field kosongnya.
  - correctable=False : hanya informasi, karena tidak bisa diisi lewat field koreksi
                        Modul 4 (Kemasan, Green-Score, Gizi siap saji).

Daftar fungsi publik:
- missing_data        : daftar kategori data kurang untuk SATU produk.
- missing_count       : ukuran kekurangan, untuk urutan "paling banyak data kosong".
- incomplete_products : SEMUA produk aktif yang belum lengkap, siap ditampilkan.
"""
from collections.abc import Mapping

from product_catalog.models import Product

from .constants import CORRECTABLE_FIELDS, NUTRITION_FIELDS, TEXT_FIELDS

# Urutan di sini = urutan chip di tampilan.
# Format: (key, label tampilan, field koreksi yang bisa mengisinya)
# Tuple field kosong () berarti kategori informasi saja (tidak bisa dikoreksi di Modul 4).
CATEGORIES = (
    ("nutrition", "Gizi", NUTRITION_FIELDS),
    ("nova", "NOVA", ("nova_group",)),
    ("brand", "Merek", ("brand",)),
    ("quantity", "Isi bersih", ("quantity",)),
    ("origin", "Asal", ("origin",)),
    ("category", "Kategori", ("category",)),
    ("prepared_nutrition", "Gizi siap saji", ()),
    ("green_score", "Green-Score", ()),
    ("packaging", "Kemasan", ()),
)

# Kebalikan dari CATEGORIES: field -> key kategorinya.
# Contoh: "fiber_100g" -> "nutrition", "brand" -> "brand".
FIELD_CATEGORY = {field: key for key, _, fields in CATEGORIES for field in fields}

# Open Food Facts menandainya (lihat TAG_FIELDS di bawah).
ALWAYS_CHECKED_FIELDS = NUTRITION_FIELDS + ("nova_group", "brand", "quantity", "origin")

# Format: tag -> key kategori
TAG_CATEGORIES = {
    "en:nutriscore-not-computed": "nutrition",
    "en:nutriscore-missing-prepared-nutrition-data": "prepared_nutrition",
    "en:environmental-score-not-computed": "green_score",
    "en:packagings-not-complete": "packaging",
}

# Format: tag -> nama field
TAG_FIELDS = {
    "en:nutriscore-missing-fiber": "fiber_100g",
    "en:nutriscore-missing-category": "category",
    "en:environmental-score-missing-data-origins": "origin",
    "en:nutriscore-missing-nutrition-data-energy": "energy_kcal_100g",
    "en:nutriscore-missing-nutrition-data-proteins": "proteins_100g",
    "en:nutriscore-missing-nutrition-data-fat": "fat_100g",
    "en:nutriscore-missing-nutrition-data-saturated-fat": "saturated_fat_100g",
    "en:nutriscore-missing-nutrition-data-sugars": "sugars_100g",
    "en:nutriscore-missing-nutrition-data-sodium": "sodium_100g",
}

# Kolom yang diambil dari database, tidak lebih (incomplete_products memakai .values()).
# Mengambil kolom seperlunya membuat query lebih ringan dibanding memuat objek Product utuh.
VALUE_FIELDS = ("pk", "product_name", "brand", "quantity", "category", "origin", "nova_group",
                *NUTRITION_FIELDS, "misc_tags")


def missing_data(product):
    """Daftar kategori data kurang untuk satu produk.

    Argumen:
        product : instance Product, atau dict hasil .values() (keduanya didukung).

    Contoh:
        produk lengkap, misc_tags []
            -> []
        fiber_100g None, misc_tags []
            -> [{"key": "nutrition", "label": "Gizi", "correctable": True, "fields": ["fiber_100g"]}]
        semua kolom terisi (termasuk nilai 0), grade "unknown"
            -> []
        misc_tags ["en:packagings-not-complete"]
            -> [{"key": "packaging", "label": "Kemasan", "correctable": False, "fields": []}]
        misc_tags ["en:nutriscore-not-computed"], semua kolom gizi terisi
            -> [{"key": "nutrition", "label": "Gizi", "correctable": False, "fields": []}]
    """
    tags = _tags(_get(product, "misc_tags"))
    found = {}  # key kategori -> set field kosong


    for field in ALWAYS_CHECKED_FIELDS:
        if _is_empty(field, _get(product, field)):
            found.setdefault(FIELD_CATEGORY[field], set()).add(field)

    for tag, field in TAG_FIELDS.items():
        if tag in tags and _is_empty(field, _get(product, field)):
            found.setdefault(FIELD_CATEGORY[field], set()).add(field)

    for tag, key in TAG_CATEGORIES.items():
        if tag in tags:
            found.setdefault(key, set())

    result = []
    for key, label, _ in CATEGORIES:
        if key in found:
            fields = [field for field in CORRECTABLE_FIELDS if field in found[key]]
            result.append({"key": key, "label": label, "correctable": bool(fields), "fields": fields})
    return result


def missing_count(missing):
    """Ukuran kekurangan: jumlah field kosong, ditambah 1 untuk tiap kategori informasi.
    Dipakai untuk urutan "Paling banyak data kosong" di antrean.

    Contoh:
        [Gizi dengan 2 field, Kemasan (info)]  -> 3
        []                                     -> 0
    """
    return sum(len(entry["fields"]) or 1 for entry in missing)


def incomplete_products(queryset=None):
    """Semua produk aktif yang belum lengkap, sebagai list ringan.
    - Hanya satu query (.values() untuk kolom yang perlu).
    - Produk nonaktif selalu dibuang, walaupun queryset yang diberikan memuatnya.
    - Urutan: missing_count menurun (paling kurang dulu), lalu pk.

    Argumen:
        queryset : opsional, untuk membatasi produk yang diperiksa. Bawaan: semua Product.

    Contoh hasil:
        [{"pk": 7, "product_name": "Sarimi Isi 2 Goreng", "brand": "Sarimi", "quantity": "88 g",
          "missing": [{"key": "nutrition", "label": "Gizi", "correctable": True,
                       "fields": ["fiber_100g", "sodium_100g"]}],
          "missing_count": 2}]
    """
    products = (queryset if queryset is not None else Product.objects.all()).filter(is_active=True)
    rows = []
    for values in products.order_by("pk").values(*VALUE_FIELDS):
        missing = missing_data(values)
        if missing:  # produk lengkap tidak masuk antrean
            rows.append({
                "pk": values["pk"],
                "product_name": values["product_name"],
                "brand": values["brand"],
                "quantity": values["quantity"],
                "missing": missing,
                "missing_count": missing_count(missing),
            })
    rows.sort(key=lambda row: (-row["missing_count"], row["pk"]))
    return rows


def _get(product, name):
    """Ambil nilai dari instance Product atau dict hasil .values().

    Contoh:
        (Product(brand="Sarimi"), "brand")  -> "Sarimi"
        ({"brand": ""}, "brand")            -> ""
    """
    return product[name] if isinstance(product, Mapping) else getattr(product, name)


def _is_empty(field, value):
    """Kosong berarti NULL, atau teks yang hanya berisi spasi. Angka 0 BUKAN kosong.

    Contoh:
        ("brand", "")         -> True
        ("brand", "  ")       -> True
        ("fat_100g", None)    -> True
        ("fat_100g", 0.0)     -> False
        ("nova_group", 1)     -> False
    """
    if value is None:
        return True
    return field in TEXT_FIELDS and not str(value).strip()


def _tags(raw):
    """misc_tags -> set berisi string tag.
    Selain list (None, dict, atau data rusak) dianggap tanpa tag, supaya satu produk
    dengan data aneh tidak membuat seluruh antrean error.

    Contoh:
        ["en:a", "en:b"]  -> {"en:a", "en:b"}
        None              -> set()
        {"x": 1}          -> set()
    """
    if not isinstance(raw, list):
        return set()
    return {tag for tag in raw if isinstance(tag, str)}