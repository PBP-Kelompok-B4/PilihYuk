# Temuan API Open Food Facts

Diuji 2 Oktober 2026, hanya baca, dengan User-Agent PilihYuk dan jeda di bawah batas resmi. Respons mentah ada di `off-samples/` (file `qN_*` merujuk nomor di bawah). Sampel 100 produk search (`q1_v2_search_sample.json`) juga dibaca tes Modul 1. Kode server yang dirujuk adalah `openfoodfacts-server` commit `d1eb237`.

Dua sumber data dipakai. Sampel 100 produk dari search condong ke produk populer, karena search mengurutkan dari yang paling sering dipindai. Populasi 8.186 produk Indonesia di dump CSV 1 Oktober tidak bias, jadi angka populasi yang dipakai untuk keputusan.

## Ringkasan

| Hal | Temuan |
|-----|--------|
| Produk berlabel Indonesia | 9.001 (API) atau 8.186 (dump), dari 4.788.440 produk |
| Subdomain `id` menyaring search v2 | Ya |
| Subdomain `id` menyaring baca barcode v3 | Tidak |
| Produk dengan minimal 4 dari 6 baris pembanding | 196 dari 8.186 (2,4%) |
| Produk tanpa satu pun baris | 7.301 (89%) |
| Grade lingkungan `a-plus` dan `f` | Ada (8 dan 11 produk) |
| 503 acak | Ya, dengan badan HTML |
| Nilai gizi kosong | Key tidak ada |

## Q1. Cakupan (populasi dump)

| Data | Terisi |
|------|--------|
| Nutri-Score a sampai e | 437 (5,3%). 7.644 `unknown`, 49 `not-applicable`, 56 kosong |
| Skor lingkungan | 341 (4,2%). 5.332 `unknown`, 36 `not-applicable`, 2.477 kosong |
| `nova_group` | 382 (4,7%) |
| Tujuh nutrien lengkap | 163 (2,0%). Minimal 6 dari 7: 298 (3,6%) |
| Asal | 341 (4,2%) |
| Kemasan | 286 (3,5%) |
| Gambar | 6.886 (84,1%) |
| Berlabel `en:halal` | 1.988 (24,3%) |

Baris pembanding yang terisi (dari 6: Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama dengan minimal 6 dari 7 nutrien): 0 baris 7.301, 1 baris 365, 2 baris 173, 3 baris 151, 4 baris 101, 5 baris 53, 6 baris 42. Minimal 4 baris: 196 produk. Sebanyak 5.987 produk bernama dan bergambar tapi paling banyak satu baris terisi, dan itu bahan antrean Modul 4.

Sampel populer jauh lebih lengkap (Nutri-Score 67%, skor lingkungan 56%), jadi jangan dipakai untuk memperkirakan katalog.

## Q2. Grade dan nama field

- Nutri-Score: `a` sampai `e`, `unknown`, `not-applicable`. `nutriscore_grade` dan `nutrition_grades` identik di API. Dump hanya punya `nutriscore_grade`.
- Skor lingkungan: `a-plus`, `a` sampai `f`, `unknown`, `not-applicable` (`lib/ProductOpener/Display.pm:2385`).
- API v2 dan v3 mengembalikan `ecoscore_grade`, tidak pernah `environmental_score_grade`, walau changelog v3.1 bilang namanya sudah diganti. Dump kebalikannya. Kode membaca nama baru dulu, lalu nama lama.
- Sel kosong, key tidak ada, `unknown`, dan `not-applicable` sama-sama tidak diperingkat.

## Q3. Skor lingkungan per negara

Grade tingkat atas sama di semua subdomain. `ecoscore_data.grades` berisi 63 negara tanpa `id`, dan server memakai `world` bila negara tidak ada (`EnvironmentalScore.pm:1915-1918`). Jadi tidak ada skor khusus Indonesia.

## Q4. Normalisasi barcode

Aturan server (`Products.pm:470`, `:493`, `:580`): ambil digit saja, UPC-A 12 digit yang valid diberi `0` di depan, 14 digit berawalan `0` kehilangan nol itu, nol di depan dibuang lalu diisi sampai 13 digit, dan 13 digit berawalan `00000` dipotong jadi EAN-8. Contoh: `089686010947` menjadi `0089686010947`, `03017620422003` menjadi `3017620422003`, `0000000000017` menjadi `00000017`.

Panjang kode di dump: 13 digit 7.806, 8 digit 357, 14 digit 17, dan 6 kode lebih dari 14 digit (dilewati).

## Q5. Nutrisi

- Nilai kosong berarti key tidak ada (API) atau sel kosong (dump), tidak pernah `null`. Nilai `0` sah.
- `energy-kcal_100g` untuk kkal. `energy_100g` selalu kJ.
- `salt_100g` dan `sodium_100g` terpisah. `sodium_100g` dalam gram (Indomie 0,3976, tampil 398 mg).
- `_serving` per sajian, `_prepared_100g` setelah disiapkan, `_modifier: "~"` perkiraan. Nilai hasil konversi bisa berekor panjang, jadi tampilan dibulatkan.
- Kunci bertanda hubung: `energy-kcal_100g` dan `saturated-fat_100g`. Grup NOVA diambil dari `nova_group` tingkat atas, bukan `nutriments.nova-group`.

## Q6. Bahasa

`product_name_id` terisi di 43 dari 100 produk sampel dan tidak ada di dump. Urutan nama: `product_name_id`, `product_name`, `product_name_en`. Taxonomy OFF punya nama Indonesia untuk 109 dari 14.717 kategori dan 7 dari 3.074 label (`en:halal` tidak termasuk), jadi antarmuka butuh peta terjemahan sendiri.

## Q7. Gambar dan lisensi

`image_url` sama dengan `image_front_url` (ukuran 400) pada semua produk bergambar. URL memuat nomor revisi, jadi berubah saat gambar diganti. Lisensi: ODbL untuk struktur, DbCL untuk isi, CC BY-SA untuk gambar. Pengguna ulang wajib menyebut lisensi dan menaut ke openfoodfacts.org atau halaman produknya.

## Q8. Error dan batas laju

- Produk tidak ada: HTTP 404 dengan JSON `product_not_found`.
- 503 muncul acak (search v2 sekitar separuh percobaan, baca v3 jarang) dengan badan HTML. Jangan memanggil `.json()` pada 5xx, dan retry dengan jeda.
- 429 tidak didokumentasikan dan tidak dipicu. Ditangani seperti 503.
- Batas resmi per IP: 15 baca produk dan 10 search per menit. Ada juga batas global yang dijawab 503.
- Waktu respons 0,7 sampai 1,1 detik. Timeout 10 detik dengan dua kali retry.

## Q9. Search

Search v2 masih bekerja walau deprecated. `page_size` maksimum 100. Urutan bawaan sama dengan `sort_by=unique_scans_n`. Dokumentasi melarang memakai search untuk menyalin katalog, jadi seeding memakai dump.

## Q10. `misc_tags`

Tag untuk deteksi data kosong: `en:nutriscore-not-computed`, `en:nutriscore-missing-nutrition-data`, `en:nutriscore-missing-prepared-nutrition-data` (Nutri-Score `unknown` walau gizi lengkap, misalnya mi instan), `en:environmental-score-not-computed`, `en:environmental-score-missing-data-packagings`, dan `en:packagings-not-complete`. Dump tidak punya `misc_tags`.

## Q11. Dump

Semua ekspor bersifat global. CSV 1,28 GB (dipakai), Parquet 7,87 GB, JSONL 13,06 GB. Unduh CSV 148 detik, saring 4.535.553 baris dengan Python stdlib 52 detik. CSV tidak punya `misc_tags` dan `product_name_id`. CSV tidak masuk repo, hanya fixture hasil saringan.

## Q12. Filter Indonesia

Baca v3 lewat `id.openfoodfacts.org` untuk Nutella tetap mengembalikan `countries_tags: ["en:france"]`, jadi subdomain tidak menyaring. Search v2 di `id` menyaring (9.001 produk). `countries_tags_en=indonesia` dan `countries_tags=en:indonesia` sama-sama bekerja. Aturan aplikasi: `isinstance(countries_tags, list) and "en:indonesia" in countries_tags`.

## Q13. Data halaman detail

| Data | Seluruh produk Indonesia | 196 produk berdata cukup |
|------|--------------------------|--------------------------|
| Teks bahan | 18,4% | 97,4% |
| Alergen | 1,9% | 54,6% |
| Berat bersih | 49,1% | 98,5% |
| Ukuran porsi | 18,7% | 94,4% |

"Dapat didaur ulang" tidak ada di OFF. Jumlah porsi dihitung dari berat bersih dan ukuran porsi.
