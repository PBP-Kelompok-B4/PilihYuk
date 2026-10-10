# Evaluasi SDK Open Food Facts untuk PilihYuk

Tanggal: 2 Oktober 2026. Status bukti memakai istilah yang sama dengan `off-api-findings.md`: *Terverifikasi*, *Dokumentasi*, *Dugaan*. Jalur kode di bawah relatif ke repo masing-masing, hasil `git clone --depth 1` ke luar proyek.

## Rekomendasi singkat

| Kebutuhan | Rekomendasi | Alasan |
|-----------|-------------|--------|
| Management command seeding | Skrip sekali jalan memakai `iter_csv()` dari `tools/check_off_encodings.py` (stdlib) untuk membuat fixture; management command cukup `loaddata`. Pembacaan v3 lewat klien `requests` tipis hanya untuk melengkapi `misc_tags` dan `product_name_id` | SDK Python hanya bisa mengunduh seluruh dump (13 GB) dan tidak punya pembungkus search v2 |
| Lookup barcode saat runtime | Klien `requests` tipis | Perlu penolakan non-Indonesia, penanganan 404 JSON dan 503 HTML, retry. SDK tidak menyediakannya |
| Refresh satu produk | Klien `requests` tipis yang sama | Sama |
| Flutter di PAS | Hanya memanggil endpoint JSON Django. SDK Dart dipakai untuk bagian kecil (lihat bawah) | Koreksi lokal, representasi `"unknown"`, rate limit, dan filter Indonesia ada di Django |

`requests` dan `urllib3` sudah ada di `PilihYuk/requirements.txt`, jadi rekomendasi ini tidak menambah dependency.

## SDK Python (`openfoodfacts`, untuk Django)

Sumber: https://github.com/openfoodfacts/openfoodfacts-python, commit `acbebb8` (22 Sep 2026).

| Aspek | Temuan | Bukti | Status |
|-------|--------|-------|--------|
| Versi dan lisensi | 5.3.0, MIT, Python 3.10 ke atas | `pyproject.toml:3`, `:9`, `:13` | Terverifikasi |
| Aktivitas | Commit terakhir 22 Sep 2026, rilis otomatis (`release-please-config.json`) | `git log` | Terverifikasi |
| Dependency terpasang | `requests`, `pydantic` (2.x), `tqdm`; ekstra `ml` opsional | `pyproject.toml:14-18`, `:74` | Terverifikasi |
| Versi API | Bawaan **v2**, bisa diganti `version="v3"` | `src/openfoodfacts/types.py:859`, `api.py:924` | Terverifikasi |
| `fields` | Didukung lewat `product.get(code, fields=[...])`; koma tidak di-escape (menghindari bug server) | `api.py:524-552` | Terverifikasi |
| User-Agent | Argumen wajib `user_agent` | `api.py:917-919`, `:47` | Terverifikasi |
| Negara dan subdomain | Argumen `country=` (enum `Country`, `id` ada); lingkungan staging otomatis memakai basic auth `off`/`off` | `api.py:922`, `:17-18`, `types.py:254`, `:505` | Terverifikasi |
| Search | `text_search` memakai `cgi/search.pl` (jalur lama); `search` memakai Search-a-licious dan bertanda **alpha**. **Tidak ada pembungkus `/api/v2/search`**, jadi filter `countries_tags` tidak didukung | `api.py:575-639` | Terverifikasi |
| Error | Memanggil `raise_for_status()`, jadi 503 menjadi `requests.HTTPError` tanpa retry. 404 menjadi `None` | `api.py:72-75`, `:561-563` | Terverifikasi |
| Timeout | Bawaan 10 detik | `types.py:863` | Terverifikasi |
| Dump | `get_dataset()` mengunduh seluruh file ke `~/.cache/openfoodfacts/datasets`. Tidak ada unduhan parsial | `dataset.py:22`, `:43-83` | Terverifikasi |
| Filter Indonesia | Tidak ada | | Terverifikasi (tidak ditemukan di `api.py`) |

Satu catatan: `ProductResource.get` mengecek `resp["status"] == 0` (`api.py:567`), bentuk status v2. Respons v3 memakai `"status": "success"` atau `"failure"` (`q12_v3_id_nutella.json`, `q8_v3_notfound.json`). Pada v3 produk tidak ada sudah jatuh ke cabang 404, jadi hasilnya tetap benar. Status: Dugaan bahwa tidak ada dampak.

### Contoh yang sudah dijalankan

**SDK**, pada 2 Oktober 2026, di venv sementara di luar proyek (SDK 5.3.0):

```python
from openfoodfacts import API
api = API(user_agent=UA, country="id", version="v3", timeout=20)
api.product.get("089686010947", fields=["code", "product_name", "countries_tags", "nutrition_grades", "ecoscore_grade"])
# {'code': '0089686010947', 'countries_tags': ['en:france', 'en:indonesia'],
#  'ecoscore_grade': 'a', 'nutrition_grades': 'unknown', 'product_name': 'Indomie Mi Goreng Original'}
api.product.get("0000000000017", fields=["code"])   # None
```

**Klien `requests` tipis**. Fungsi `normalize_barcode` dan `is_indonesian` berasal dari `tools/check_off_encodings.py`:

```python
def fetch_product(raw_code):
    """Return (status, product): 'ok' | 'not_found' | 'not_indonesian'. Raises OffUnavailable."""
    code = normalize_barcode(raw_code)
    url = f"https://id.openfoodfacts.org/api/v3/product/{code}"
    for wait in (5, 15, None):                     # retry 5xx / network errors
        try:
            r = requests.get(url, params={"fields": FIELDS}, headers={"User-Agent": UA}, timeout=10)
            if r.status_code == 404:
                return "not_found", None
            if r.status_code < 500:
                r.raise_for_status()
                product = r.json()["product"]
                return ("ok", product) if is_indonesian(product) else ("not_indonesian", product)
        except requests.RequestException:
            pass
        if wait is None:
            raise OffUnavailable(code)             # 503 body is HTML, never call .json() on it
        time.sleep(wait)
```

Hasil jalan: `089686010947 -> ok 0089686010947 Indomie Mi Goreng Original`; `3017620422003 -> not_indonesian 3017620422003 Nutella`; `0000000000017 -> not_found`.

### Keputusan per kebutuhan

- **Seeding.** SDK tidak membantu: `get_dataset` memaksa unduhan penuh dan tidak ada search v2. Jalur yang dipilih ada di `off-api-findings.md` (Q11): `iter_csv()` menyaring dump CSV, hasilnya fixture Django, dan management command cukup `loaddata`. Klien tipis hanya melengkapi `misc_tags` dan `product_name_id`, yang tidak ada di CSV.
- **Lookup runtime.** Klien tipis. Bedanya dengan SDK: mengembalikan tiga status eksplisit (bukan `None` untuk "tidak ada"), menolak produk non-Indonesia sebelum menyentuh basis data, dan menangani 503 HTML.
- **Refresh.** Klien yang sama, lalu `is_indonesian()` dicek lagi. Aturan koreksi `DataCorrection` diterapkan di lapisan model, bukan di klien.
- **Batas laju di sisi Django.** Seluruh pengguna web berbagi satu alamat IP server PWS. Batas OFF 15 request per menit untuk baca produk (Dokumentasi) berarti seluruh lookup runtime dari semua pengguna berbagi anggaran itu. Lookup perlu dibatasi per pengguna dan, bila perlu, diantre. Status: Dugaan bahwa PWS keluar lewat satu IP.

## SDK Dart (`openfoodfacts`, untuk Flutter di PAS)

Sumber: https://github.com/openfoodfacts/openfoodfacts-dart, commit `7e257d5` (2 Okt 2026).

| Aspek | Temuan | Bukti | Status |
|-------|--------|-------|--------|
| Versi, lisensi, aktivitas | 3.30.2, Apache-2.0, commit terakhir 2 Okt 2026 | `pubspec.yaml:4`, `LICENSE`, `git log` | Terverifikasi |
| Dependency | `json_annotation`, `http`, `path`, `meta`. Dart SDK 3.11 ke atas | `pubspec.yaml:8`, `:10-14` | Terverifikasi |
| Baca produk | `OpenFoodAPIClient.getProductV3(config)` | `lib/src/open_food_api_client.dart:286` | Terverifikasi |
| Search | `searchProducts(...)`, dengan `TagFilter` bertipe `COUNTRIES` | `open_food_api_client.dart:473`, `lib/src/model/parameter/tag_filter.dart:15` | Terverifikasi |
| Model `Product` | Kelas besar dengan banyak field bernilai `String?` atau `double?` | `lib/src/model/product.dart` | Terverifikasi |
| Eco-Score / Green-Score | `ecoscoreGradeV3` (key `ecoscore_grade`) ditandai deprecated, diganti `environmentalScoreGrade` dengan catatan "API V3.1+"; juga `EcoscoreData` | `product.dart:623-634`, `lib/src/model/ecoscore_data.dart` | Terverifikasi |
| Konfigurasi global | `userAgent`, `globalLanguages`, `globalCountry`; enum negara memuat `INDONESIA` (`offTag: 'id'`) | `lib/src/utils/open_food_api_configuration.dart:43`, `:54`, `:59`; `country_helper.dart:420` | Terverifikasi |
| Validasi barcode | `barcodes_validator.dart`, `invalid_barcodes.dart` | `lib/src/utils/` | Terverifikasi (nama file; isi tidak dibaca) |
| Pembatas laju | `TooManyRequestsManager` (throttle sisi klien berdasarkan `maxCount` dan `duration`) | `lib/src/utils/too_many_requests_manager.dart` | Terverifikasi |
| Lainnya | Gambar, knowledge panels, Robotoff, folksonomy, prices, taxonomy, dan **`saveProduct`** (tulis ke produksi) | `lib/src/` | Terverifikasi |
| Scanner kamera | **Tidak ada**: kata `camera`, `mobile_scanner`, `mlkit` tidak muncul di `pubspec.yaml` maupun `lib/` | grep | Terverifikasi |

SDK Dart belum dijalankan: tidak ada toolchain Flutter di mesin ini dan PAS belum dimulai. Klaim fungsionalnya berstatus Dokumentasi/baca kode, bukan eksekusi.

### Apakah Flutter memanggil OFF langsung?

**Rekomendasi: tidak. Flutter hanya memanggil endpoint JSON Django.** Pertimbangan, mengikuti daftar di tugas:

| Pertimbangan | Jika Flutter langsung ke OFF | Jika lewat Django |
|--------------|------------------------------|-------------------|
| Koreksi `DataCorrection` dan shelf (hanya di basis data lokal) | Aplikasi harus menimpa data OFF dengan koreksi dari Django, dua sumber untuk satu produk | Satu sumber. Koreksi sudah menyatu |
| Representasi `"unknown"` | Aplikasi menerima nama field dan nilai mentah OFF (`ecoscore_grade` vs `environmental_score_grade`, grade `unknown` vs `not-applicable`), harus menormalkan sendiri | Django menormalkan sekali (aturan di README) |
| Rate limit | Batas OFF berlaku per pengguna bila request datang dari aplikasi pengguna (Dokumentasi, `docs/api/index.md:56`), jadi tidak berbagi anggaran | Semua pengguna berbagi satu anggaran 15 request per menit dari IP server. Cache lokal dan pembatasan per pengguna wajib |
| Offline | SDK tidak menyimpan cache; aplikasi harus menyediakan sendiri | Django melayani dari basis data. Aplikasi menyimpan hasil JSON terakhir untuk offline |
| Filter Indonesia | Aturan `is_indonesian()` ditulis ulang di Dart dan dijaga selaras | Satu implementasi di Django |
| Skor estimasi dan produk manual | Tidak ada di OFF | Ada di Django |

Satu-satunya keuntungan jalur langsung adalah pembagian rate limit, dan itu bisa diatasi di Django lewat cache dan penyimpanan lokal.

### Kapan SDK Dart tetap berguna

- **Pemindai barcode di PAS**: SDK tidak menyediakan scanner. Aplikasi memakai paket kamera terpisah. Hasil pindai diteruskan sebagai string ke endpoint Django.
- **Validasi barcode di sisi klien** (`barcodes_validator.dart`) sebelum memanggil Django, supaya salah ketik tidak menghabiskan request.
- **Rujukan nama field dan model** `Product` untuk mendesain kelas Dart sendiri. Kelas itu sebaiknya dipetakan dari JSON Django, bukan memakai `Product` SDK, karena field Django berbeda (misalnya `environmental_grade_estimated`, `source`).
- **Cadangan bila suatu hari Django tidak dipakai sebagai perantara**: SDK sudah menyediakan klien, parser, dan `TooManyRequestsManager`. Aturan `is_indonesian()` harus ditulis ulang di Dart.
- Jangan memakai `saveProduct` dan fungsi tulis lain: proyek ini tidak mengirim koreksi balik ke OFF.

## Implikasi ke kontrak JSON Django yang dibuat sekarang

Tujuan: PAS tidak memaksa perubahan model.

| Hal | Aturan yang disarankan |
|-----|------------------------|
| Nama field | Gunakan nama kolom model Django (`product_name`, `brand`, `nutrition_grade`, `environmental_grade`, `environmental_grade_estimated`, `nova_group`, `energy_kcal_100g`, ...), `snake_case`, bukan nama OFF. Satu pemetaan OFF ke Django di satu tempat |
| Grade | Selalu string, tidak pernah `null`: `a` sampai `e` (skor lingkungan juga `f` dan `a-plus`), `"unknown"`, `"not-applicable"`. Dart memakai enum dengan nilai cadangan untuk nilai tak dikenal, agar tingkat baru tidak membuat aplikasi macet |
| Angka | `nova_group` dan kolom gizi bernilai `null` bila kosong, tidak pernah `0` untuk "kosong". `0` berarti nilai nol yang sah (garam 0 ada di sampel). Ditulis sebagai angka JSON, bukan string |
| Barcode | Selalu **string**, hasil `normalize_barcode()`, tidak pernah angka (nol di depan hilang bila angka). Bisa 8, 13, atau 14 digit. `null` untuk produk manual tanpa barcode |
| Estimasi | Pisahkan `environmental_grade` (resmi) dan `environmental_grade_estimated`. Tambahkan boolean turunan `environmental_is_estimated` agar Dart tidak menebak dari dua field |
| Gambar | Satu field `image_url` (ukuran 400). Ukuran lain dibentuk dari URL OFF bila diperlukan, belum perlu sekarang |
| Sumber | `source` (`off`/`manual`) dan `last_synced_at` (ISO 8601) disertakan |
| Paginasi | Selubung `{"count", "page", "page_size", "results"}`, mengikuti bentuk OFF |
| Error JSON | Satu bentuk: `{"error": {"id": "...", "message": "..."}}` dengan kode HTTP yang sesuai. Termasuk `product_not_found` dan `not_indonesian` |
| Atribusi | Sertakan `off_url` (halaman produk OFF) pada produk `source=off`, untuk tautan atribusi |

Dampak ke ERD: tidak ada kolom baru selain yang sudah ada di model Product, kecuali ada keputusan baru. `environmental_is_estimated` dan `off_url` dihitung saat serialisasi, bukan disimpan.
