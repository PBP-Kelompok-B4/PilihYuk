"""Akses data Open Food Facts (OFF) untuk katalog PilihYuk.

Dipakai di dua tempat:
- lookup barcode dan refresh produk di view, lewat fetch_product()
- perintah seeding, lewat read_indonesian_products_from_csv()

Dokumentasi API: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

import csv
import gzip
import time

import requests

API_BASE_URL = "https://id.openfoodfacts.org"
USER_AGENT = (
    "PilihYuk/0.1 (PBP Fasilkom UI; https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/; "
    "https://github.com/pbp-Kelompok-B4/PilihYuk/)"
)
INDONESIA_TAG = "en:indonesia"

# Field yang diminta dari API. Daftar ini mengikuti kolom model Product.
PRODUCT_FIELDS = [
    "code",
    "product_name",
    "product_name_id",
    "product_name_en",
    "brands",
    "quantity",
    "image_url",
    "categories_tags",
    "labels_tags",
    "countries_tags",
    "origins_tags",
    "manufacturing_places",
    "packaging_tags",
    "ingredients_analysis_tags",
    "ingredients_text_id",
    "ingredients_text",
    "allergens_tags",
    "serving_size",
    "nutriments",
    "misc_tags",
    "nutriscore_grade",
    "nutrition_grades",
    "nova_group",
    "environmental_score_grade",
    "ecoscore_grade",
]

# OFF tidak memakai null. Nilai kosong ditulis sebagai teks berikut.
EMPTY_VALUES = {"", "unknown", "not-applicable"}

# OFF kadang membalas 429 (terlalu banyak permintaan) atau 503 (server sibuk).
# Angka di tuple adalah lama menunggu (detik) sebelum mencoba lagi.
RETRY_STATUS_CODES = {429, 503}
SHORT_RETRY_WAITS = (2, 5)  # untuk view: pengguna sedang menunggu halaman
LONG_RETRY_WAITS = (15, 30, 60)  # untuk perintah yang berjalan di terminal

# Kolom CSV yang berisi daftar dipisah koma, diubah menjadi list Python.
CSV_LIST_COLUMNS = [
    "categories_tags",
    "labels_tags",
    "countries_tags",
    "origins_tags",
    "packaging_tags",
    "ingredients_analysis_tags",
    "allergens_tags",
]
CSV_MAX_CELL_SIZE = 2**31 - 1  # beberapa sel teks bahan sangat panjang


def get_json(url, params=None, retry_waits=LONG_RETRY_WAITS):
    """GET ke OFF dan kembalikan isi JSON-nya.

    Mencoba ulang saat OFF membalas 429 atau 503. Status gagal lain, atau gagal
    setelah percobaan terakhir, menimbulkan requests.HTTPError.
    """
    headers = {"User-Agent": USER_AGENT}
    for wait_seconds in [*retry_waits, None]:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        if response.status_code in RETRY_STATUS_CODES and wait_seconds is not None:
            time.sleep(wait_seconds)
            continue
        # 503 dari OFF berupa halaman HTML, jadi cek status sebelum membaca JSON.
        response.raise_for_status()
        return response.json()


def fetch_product(barcode):
    """Ambil satu produk dari API v3. Kembalikan None bila barcode tidak ada di OFF."""
    url = f"{API_BASE_URL}/api/v3/product/{barcode}"
    params = {"fields": ",".join(PRODUCT_FIELDS)}
    try:
        data = get_json(url, params, retry_waits=SHORT_RETRY_WAITS)
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            return None
        raise
    return data.get("product")


def normalize_barcode(raw_barcode):
    """Samakan barcode dengan format yang disimpan OFF.

    Meniru normalize_code di server OFF (lib/ProductOpener/Products.pm):
    1. Ambil digitnya saja.
    2. UPC 12 digit yang valid diberi satu angka 0 di depan.
    3. Kode 14 digit yang diawali 0 kehilangan angka 0 itu.
    4. Angka 0 di depan dibuang, lalu kode dipadatkan dengan 0 sampai 13 digit.
    5. Kode 13 digit yang diawali 00000 menjadi EAN-8 (8 digit).
    """
    if raw_barcode is None:
        return None
    barcode = "".join(char for char in str(raw_barcode) if char.isdigit())
    if has_valid_upc_check_digit(barcode):
        barcode = "0" + barcode
    if len(barcode) == 14 and barcode.startswith("0"):
        barcode = barcode[1:]
    if not barcode:
        return barcode
    barcode = barcode.lstrip("0").rjust(13, "0")
    if len(barcode) == 13 and barcode.startswith("00000"):
        barcode = barcode[5:]
    return barcode


def has_valid_upc_check_digit(barcode):
    """True bila barcode berupa UPC-A: 12 digit dengan digit terakhir yang cocok."""
    if len(barcode) != 12 or not barcode.isdigit():
        return False
    digits = [int(char) for char in barcode]
    odd_position_sum = sum(digits[0:11:2])
    even_position_sum = sum(digits[1:11:2])
    expected_check_digit = (10 - (odd_position_sum * 3 + even_position_sum) % 10) % 10
    return digits[11] == expected_check_digit


def is_sold_in_indonesia(product):
    """True bila produk dijual di Indonesia (countries_tags memuat en:indonesia).

    Ini bukan negara asal produk; asal produk ada di origins_tags dan
    manufacturing_places. Aturan ini dipakai di seeding, lookup, dan refresh.
    """
    if not isinstance(product, dict):
        return False
    countries = product.get("countries_tags")
    return isinstance(countries, list) and INDONESIA_TAG in countries


def has_value(product, field):
    """True bila field terisi. "unknown", "not-applicable", teks kosong, dan list kosong dianggap kosong."""
    value = product.get(field)
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in EMPTY_VALUES
    if isinstance(value, list):
        return len(value) > 0
    return True


def read_indonesian_products_from_csv(path, limit=None):
    """Baca dump CSV OFF baris demi baris dan hasilkan produk yang dijual di Indonesia.

    File CSV-nya besar (sekitar 1,3 GB), jadi dibaca sedikit demi sedikit, tidak sekaligus.
    Tiap baris dibentuk mirip produk dari API supaya kode seeding cukup satu:
    sel kosong dibuang, kolom daftar menjadi list, nutriscore_grade disalin ke
    nutrition_grades, dan kolom *_100g dikumpulkan ke dict nutriments.
    Catatan: CSV tidak punya misc_tags dan product_name_id.
    """
    csv.field_size_limit(CSV_MAX_CELL_SIZE)
    open_file = gzip.open if path.endswith(".gz") else open
    found = 0
    with open_file(path, "rt", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter="\t", quoting=csv.QUOTE_NONE):
            if INDONESIA_TAG not in (row.get("countries_tags") or ""):
                continue  # saringan cepat; jutaan baris lain dilewati tanpa diproses
            product = {column: value for column, value in row.items() if column and value}
            for column in CSV_LIST_COLUMNS:
                if column in product:
                    product[column] = product[column].split(",")
            if not is_sold_in_indonesia(product):
                continue
            if "nutriscore_grade" in product:
                product["nutrition_grades"] = product["nutriscore_grade"]
            if is_number(product.get("nova_group")):
                product["nova_group"] = int(float(product["nova_group"]))
            product["nutriments"] = {
                column: float(value)
                for column, value in product.items()
                if column.endswith("_100g") and is_number(value)
            }
            yield product
            found += 1
            if limit and found >= limit:
                return


def is_number(value):
    """True bila value bisa diubah menjadi angka, misalnya "4" atau "0.5"."""
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True
