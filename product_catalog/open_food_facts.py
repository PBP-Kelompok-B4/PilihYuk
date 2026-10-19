"""Akses data Open Food Facts (OFF) untuk katalog PilihYuk.

Dipakai di dua tempat:
- lookup barcode dan refresh produk di view, lewat fetch_product()
- perintah seeding, lewat read_indonesian_products_from_csv()

Dokumentasi API: https://openfoodfacts.github.io/openfoodfacts-server/api/
"""

import csv
import gzip
import math
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

# Retry 429 (rate limit) and transient HTTP 5xx responses.
# Angka di tuple adalah lama menunggu (detik) sebelum mencoba lagi.
RETRY_STATUS_CODES = {429, *range(500, 600)}
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

    Retry 429, all 5xx, and network failures; never retry invalid JSON or 4xx.
    Each request has a 10-second timeout. Delays bound the number of retries.
    """
    headers = {"User-Agent": USER_AGENT}
    for wait_seconds in [*retry_waits, None]:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
        except (
            requests.Timeout, requests.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ContentDecodingError,
        ):
            if wait_seconds is None:
                raise
            time.sleep(wait_seconds)
            continue
        if response.status_code in RETRY_STATUS_CODES and wait_seconds is not None:
            time.sleep(wait_seconds)
            continue
        # 503 dari OFF berupa halaman HTML, jadi cek status sebelum membaca JSON.
        response.raise_for_status()
        return response.json()


def fetch_product(barcode):
    """Return a product dict or None for explicit not-found responses.

    Malformed decoded payloads raise ValueError, like invalid JSON; they are
    not retried and must not be mistaken for an absent product.
    """
    url = f"{API_BASE_URL}/api/v3/product/{barcode}"
    params = {"fields": ",".join(PRODUCT_FIELDS)}
    try:
        data = get_json(url, params, retry_waits=SHORT_RETRY_WAITS)
    except requests.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            return None
        raise
    if not isinstance(data, dict):
        raise ValueError("OFF response must be a dictionary")
    if "product" not in data:
        result = data.get("result")
        if (type(data.get("status")) is int and data["status"] == 0) or (
            isinstance(result, dict) and result.get("id") == "product_not_found"
        ):
            return None
        raise ValueError("OFF response is missing product without a not-found marker")
    if not isinstance(data["product"], dict):
        raise ValueError("OFF response product must be a dictionary")
    return data["product"]


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
    barcode = "".join(char for char in str(raw_barcode) if char in "0123456789")
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
    if not isinstance(barcode, str) or len(barcode) != 12 or not barcode.isascii() or not barcode.isdigit():
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


def read_indonesian_products_from_csv(path, limit=None, stats=None, reject_callback=None):
    """Baca dump CSV OFF baris demi baris dan hasilkan produk yang dijual di Indonesia.

    File CSV-nya besar (sekitar 1,3 GB), jadi dibaca sedikit demi sedikit, tidak sekaligus.
    Tiap baris dibentuk mirip produk dari API supaya kode seeding cukup satu:
    sel kosong dibuang, kolom daftar menjadi list, nutriscore_grade disalin ke
    nutrition_grades, dan kolom *_100g dikumpulkan ke dict nutriments.
    Catatan: CSV tidak punya misc_tags dan product_name_id.
    """
    csv.field_size_limit(CSV_MAX_CELL_SIZE)
    open_file = gzip.open if str(path).endswith(".gz") else open
    found = 0
    stats = stats if stats is not None else {}

    def count(key):
        stats[key] = stats.get(key, 0) + 1

    with open_file(path, "rt", encoding="utf-8-sig", newline="") as file:
        # Detect from the header only: never read the dump into memory.
        header = file.readline()
        try:
            dialect = csv.Sniffer().sniff(header, delimiters="\t,;")
        except csv.Error as exc:
            raise ValueError("CSV header delimiter is not supported") from exc
        file.seek(0)
        # OFF TSV exports have literal, unescaped quotes (verified in the dump).
        # Preserve the existing QUOTE_NONE behavior for tabs; ordinary CSV uses quotes.
        quoting = csv.QUOTE_NONE if dialect.delimiter == "\t" else csv.QUOTE_MINIMAL
        reader = csv.reader(file, dialect=dialect, quoting=quoting, strict=True)
        columns = next(reader, [])
        if len(columns) != len(set(columns)) or not {"code", "countries_tags"}.issubset(columns):
            raise ValueError("CSV requires unique headers including code and countries_tags")
        stats["delimiter"] = dialect.delimiter
        stats["encoding"] = "utf-8-sig"
        stats["quoting"] = "literal" if quoting == csv.QUOTE_NONE else "csv"
        stats["columns"] = columns
        country_index = columns.index("countries_tags")
        report_indexes = {key: columns.index(key) for key in
                          ("code", "product_name", "product_name_id", "product_name_en", "nutriscore_grade", "nutrition_grades")
                          if key in columns} if reject_callback else {}
        def rejected(cells, reason):
            if reject_callback:
                reject_callback({key: cells[index] for key, index in report_indexes.items()
                                 if index < len(cells)}, reason)
        for cells in reader:
            count("rows_read")
            if len(cells) != len(columns):
                count("malformed_row")
                rejected(cells, "malformed_row")
                continue
            countries = [tag.strip() for tag in cells[country_index].split(",") if tag.strip()]
            if INDONESIA_TAG not in countries:
                count("non_indonesia")
                rejected(cells, "non_indonesia")
                continue
            count("indonesia_rows")
            # Build field dictionaries only for the Indonesian subset.
            row = dict(zip(columns, cells))
            product = {
                column: value for column, value in row.items()
                if column and value and (column in {"code", "nutriscore_grade", "nutrition_grades"} or value.strip().lower() not in {"null", "none", "nan"})
            }
            # CSV missing markers are normalized here, not in the strict API mapper.
            for column in ("nutriscore_grade", "nutrition_grades", "environmental_score_grade", "ecoscore_grade"):
                if column in product:
                    product[column] = product[column].strip().lower()
            for column in CSV_LIST_COLUMNS:
                if column in product:
                    product[column] = [tag.strip() for tag in product[column].split(",") if tag.strip().lower() not in EMPTY_VALUES]
            if "allergens" in product:
                product["allergens_tags"] = [
                    tag.strip() for tag in product["allergens"].split(",")
                    if tag.strip().startswith("en:")
                ]
            if not is_sold_in_indonesia(product):
                continue
            if "nutriscore_grade" in product and "nutrition_grades" not in product:
                product["nutrition_grades"] = product["nutriscore_grade"]
            if is_number(product.get("nova_group")) and float(product["nova_group"]).is_integer():
                product["nova_group"] = int(float(product["nova_group"]))
            else:
                product.pop("nova_group", None)
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
        return not isinstance(value, bool) and math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False
