# open_food_facts.py

File ini menghubungkan Open Food Facts (OFF) dengan tabel `Product`. Isinya mengambil dan merapikan data dari OFF. Menyimpan ke database tetap tugas kode di `product_catalog` (view dan perintah seeding).

## Cara memasang

1. Salin `open_food_facts.py` dan `tests.py` dari `.claude/pilihyuk-docs/drafts/product_catalog/` ke folder `product_catalog/` di root proyek. `tests.py` menggantikan stub bawaan.
2. Jalankan `python manage.py test`. Lima tes di `product_catalog/tests.py` harus lulus. Tes tidak memanggil internet.
3. Commit di branch modul.

Tidak ada dependency baru. File ini memakai `requests`, yang sudah ada di `requirements.txt`.

## Kapan dipakai

| Alur | Fungsi yang dipanggil | Siapa yang memanggil |
|------|-----------------------|----------------------|
| Seeding awal dari dump CSV | `read_indonesian_products_from_csv()` | Perintah seeding (`product_catalog/management/commands/`) |
| Tambah produk lewat barcode | `normalize_barcode()`, `fetch_product()`, `is_sold_in_indonesia()` | View lookup barcode |
| Refresh satu produk | `fetch_product()`, `is_sold_in_indonesia()` | View atau perintah refresh |
| Cek nilai kosong saat memetakan ke `Product` | `has_value()` | Kode pemetaan OFF ke `Product` |

Alur lookup barcode:

```
barcode dari pengguna
  -> normalize_barcode()
  -> sudah ada di Product?  ya: tampilkan produknya
  -> fetch_product()
       None                        : "tidak ditemukan", tawarkan isi manual
       is_sold_in_indonesia() salah: tolak, tawarkan isi manual
       benar                       : petakan ke Product dan simpan (source="off")
```

## Fungsi

### `fetch_product(barcode)`

Mengambil satu produk dari API v3 OFF. Mengembalikan dict produk, atau `None` kalau barcode tidak ada di OFF.

```python
from product_catalog.open_food_facts import fetch_product, normalize_barcode

product = fetch_product(normalize_barcode("089686010947"))
product["product_name"]    # "Indomie Mi Goreng Original"
product["countries_tags"]  # [..., "en:indonesia"]
```

Hanya field di `PRODUCT_FIELDS` yang diminta, supaya respons kecil. Kalau OFF sibuk (429 atau 503), fungsi mencoba lagi setelah 2 lalu 5 detik. Kalau tetap gagal, muncul `requests.HTTPError`, jadi view perlu menangkapnya dan menampilkan pesan "coba lagi nanti".

### `normalize_barcode(raw_barcode)`

Menyamakan barcode dengan format yang disimpan OFF, supaya produk yang sama tidak tersimpan dua kali. Selalu panggil sebelum mencari di database atau di OFF.

```python
normalize_barcode("089686010947")       # "0089686010947"  (UPC 12 digit diberi 0 di depan)
normalize_barcode(" 3017-6204 22003 ")  # "3017620422003"  (selain digit dibuang)
normalize_barcode("17")                 # "00000017"       (EAN-8)
```

Aturannya meniru server OFF dan tertulis bernomor di docstring fungsi.

### `is_sold_in_indonesia(product)`

Benar kalau `countries_tags` memuat `en:indonesia`. Artinya produk dijual di Indonesia, bukan dibuat di Indonesia (asal produk ada di `origins_tags` dan `manufacturing_places`). Ini satu-satunya aturan "hanya produk Indonesia", dipakai di seeding, lookup, dan refresh.

Subdomain `id.openfoodfacts.org` tidak menyaring pembacaan barcode, jadi pengecekan ini wajib.

### `has_value(product, field)`

OFF tidak memakai `null`. Nilai kosong ditulis `"unknown"`, `"not-applicable"`, teks kosong, atau field-nya tidak ada sama sekali. Fungsi ini menganggap semua itu kosong.

```python
has_value({"brands": "Indomie"}, "brands")                       # True
has_value({"nutrition_grades": "unknown"}, "nutrition_grades")   # False
has_value({}, "quantity")                                         # False
```

Pakai untuk kolom teks dan angka: kalau `has_value()` salah, simpan kosong (`None` untuk angka, `""` untuk teks). Kolom grade berbeda, lihat tabel pemetaan di bawah.

### `read_indonesian_products_from_csv(path, limit=None)`

Membaca dump CSV OFF (`en.openfoodfacts.org.products.csv`, boleh `.gz`) baris demi baris dan menghasilkan produk yang dijual di Indonesia. File-nya sekitar 1,3 GB, jadi tidak dimuat sekaligus.

Tiap baris dibentuk mirip produk dari API, supaya kode pemetaan ke `Product` cukup satu:

- sel kosong dibuang
- kolom tag (`countries_tags`, `labels_tags`, dan lainnya) menjadi list
- `nutriscore_grade` disalin ke `nutrition_grades`
- semua kolom `*_100g` dikumpulkan ke dict `nutriments`

```python
for product in read_indonesian_products_from_csv("en.openfoodfacts.org.products.csv", limit=20):
    print(product["code"], product.get("product_name"))
```

`limit=20` berguna untuk membuat fixture kecil.

Bedanya dengan API: CSV tidak punya `misc_tags`, `product_name_id`, dan `allergens_tags`. Alergen ada di kolom teks `allergens`; pakai hanya token yang diawali `en:`.

### `get_json(url, params=None, retry_waits=LONG_RETRY_WAITS)`

Dipakai oleh `fetch_product()`. Mengirim GET dengan User-Agent PilihYuk (diwajibkan OFF), mencoba ulang saat 429 atau 503, dan mengecek status sebelum membaca JSON (503 dari OFF berupa halaman HTML). Biasanya tidak perlu dipanggil langsung.

`SHORT_RETRY_WAITS` (2 dan 5 detik) untuk view, karena pengguna sedang menunggu. `LONG_RETRY_WAITS` (15, 30, 60 detik) untuk perintah di terminal.

### `has_valid_upc_check_digit(barcode)` dan `is_number(value)`

Fungsi bantu untuk `normalize_barcode()` dan pembaca CSV.

## Memetakan ke `Product`

File ini tidak menyimpan apa pun. Saat menulis pemetaan, ikuti ERD dan aturan berikut:

| Kolom `Product` | Sumber di data OFF |
|-----------------|--------------------|
| `code` | `code`. Lewati produk yang kodenya lebih dari 14 karakter |
| `product_name` | `product_name_id`, kalau kosong `product_name`, kalau kosong `product_name_en` |
| `brand` | `brands` (bisa berisi beberapa merek dipisah koma) |
| `image_url` | `image_url` |
| `origin` | `origins_tags` atau `manufacturing_places`, bukan `countries_tags` |
| `nutrition_grade` | `nutriscore_grade`, kalau tidak ada `nutrition_grades`. Simpan apa adanya, termasuk `"unknown"` dan `"not-applicable"` |
| `environmental_grade` | `environmental_score_grade`, kalau tidak ada `ecoscore_grade`. Nilainya `a-plus`, `a` sampai `f`, `"unknown"`, atau `"not-applicable"` |
| `nova_group` | `nova_group` di tingkat atas (bukan di `nutriments`) |
| kolom gizi | dari `nutriments`. Nama key OFF memakai tanda hubung: `energy-kcal_100g` ke `energy_kcal_100g`, `saturated-fat_100g` ke `saturated_fat_100g`. `sodium_100g` dalam gram (tampil dalam mg di halaman) |
| `halal_labeled` | benar kalau `labels_tags` memuat `en:halal` |
| `ingredients_text` | `ingredients_text_id`, kalau kosong `ingredients_text` |
| `allergens` | `allergens_tags` (API) atau token `en:` dari kolom `allergens` (CSV) |
| `serving_size` | `serving_size` |
| tag lain | `categories_tags`, `packaging_tags`, `labels_tags`, `ingredients_analysis_tags`, `misc_tags` disimpan di `JSONField` |
| `source` | `"off"` |

## Yang tidak ada di file ini

- Batas 3 lookup per menit per pengguna. Pasang di view lookup barcode, karena semua pengguna berbagi satu alamat server dan OFF hanya mengizinkan 15 permintaan per menit per alamat.
- Filter katalog. Filter berjalan pada tabel `Product` di database, bukan pada API.
- Pencarian produk lewat API (`/api/v2/search`). Tidak dibutuhkan, karena katalog diisi dari seeding.
