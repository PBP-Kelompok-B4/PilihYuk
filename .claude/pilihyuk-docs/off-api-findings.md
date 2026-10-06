# Temuan API Open Food Facts untuk PilihYuk

Tanggal uji: 2 Oktober 2026. Semua request hanya membaca, memakai `User-Agent: PilihYuk/0.1 (PBP Fasilkom UI; https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/; https://github.com/pbp-Kelompok-B4/PilihYuk/)`, dan diberi jeda di bawah batas resmi.

**Status bukti:** *Terverifikasi* = dibuktikan dengan respons API atau kode. *Dokumentasi* = tertulis di dokumen, belum diuji. *Dugaan* = kesimpulan sendiri.

**Sumber bukti.**
- Respons mentah: `off-samples/` (di folder `pilihyuk-docs/`) (nama file `qN_*` merujuk ke nomor pertanyaan).
- Rekap skrip: `off-samples/run_check_off_encodings.txt` (hasil `tools/check_off_encodings.py`).
- Kode server: `openfoodfacts-server` commit `d1eb237`, jalur relatif ke repo itu.
- SDK: `openfoodfacts-python` commit `acbebb8`, `openfoodfacts-dart` commit `7e257d5`.
- Dokumen: https://openfoodfacts.github.io/openfoodfacts-server/api/

**Dua sumber sampel, dan yang kedua lebih benar.**
1. *Sampel API, 100 produk* (search v2). Search mengurutkan produk dari yang paling sering dipindai (tiga produk pertama pada `sort_by=unique_scans_n` sama dengan urutan bawaan, `q9_sort_scans.json`), jadi sampel ini condong ke produk populer. Buktinya: 20 produk pertama yang dibaca ulang lewat v3 punya cakupan lebih tinggi (Nutri-Score 85%, asal 80%) daripada 100 produk (67%, 56%).
2. *Populasi dump CSV, 8.186 produk Indonesia* (`run_check_off_encodings_csv.txt`, `q1_csv_population_stats.txt`). Ini seluruh produk Indonesia di ekspor 1 Okt 2026, tanpa bias popularitas. CSV dan API sepakat pada 96 dari 99 produk untuk Nutri-Score dan 91 dari 99 untuk skor lingkungan (selisih karena beda waktu ekspor), jadi angkanya bisa dipercaya.

**Cakupan sebenarnya jauh lebih rendah daripada sampel API.** Nutri-Score terisi 5,3% di populasi, bukan 67%. Seratus produk populer menampung 67 dari 437 produk ber-Nutri-Score di seluruh Indonesia. Semua angka "sampel" di Q1 sampai Q10 di bawah berlaku untuk produk populer; angka populasi diberi label tersendiri.

## Ringkasan

| Hal | Temuan | Status |
|-----|--------|--------|
| Produk berlabel Indonesia | 9.001 (API) atau 8.186 (CSV 1 Okt) dari 4.788.440 produk | Terverifikasi |
| Subdomain `id` menyaring search v2 | Ya | Terverifikasi |
| Subdomain `id` menyaring baca barcode v3 | **Tidak** | Terverifikasi |
| Produk dengan minimal 4 dari 6 baris pembanding | **196 dari 8.186 (2,4%)** di populasi; 50 sampai 54% hanya di sampel populer | Terverifikasi |
| Produk tanpa satu pun dari 6 baris | 7.301 dari 8.186 (89%) | Terverifikasi |
| Tingkat grade lingkungan | `a-plus` ada (8 produk), `f` ada (11) | Terverifikasi |
| Dump CSV vs API | CSV memakai `environmental_score_grade`, tanpa `misc_tags` dan `product_name_id` | Terverifikasi |
| Server membalas 503 acak | Ya, HTML bukan JSON | Terverifikasi |
| Nilai gizi kosong | Key tidak ada | Terverifikasi |
| Nama key gizi | Dua key memakai tanda hubung (`energy-kcal`, `saturated-fat`) | Terverifikasi |

## Q1. Cakupan

Sampel: 100 produk dari `id.openfoodfacts.org/api/v2/search?countries_tags_en=indonesia` (`q1_v2_search_sample.json`). Ke-100 produk punya `en:indonesia` di `countries_tags`.

| Data | Terisi dan bisa diperingkat | Catatan |
|------|-----------------------------|---------|
| `nutrition_grades` a sampai e | 67% | 30 `unknown`, 3 `not-applicable` |
| Skor lingkungan (`ecoscore_grade` a sampai f) | 56% | 34 `unknown`, 10 `not-applicable` |
| `nova_group` | 60% | Key tidak ada pada 40 produk |
| Tujuh nutrien di tabel Product | 54% | Serat paling jarang (58%); lainnya 78 sampai 82% |
| Asal (`origins_tags` atau `manufacturing_places`) | 56% | `origins_tags` 36%, `manufacturing_places` 39% |
| `packaging_tags` | 38% | |
| URL gambar | 98% | |
| `brands` / `quantity` / `categories_tags` | 92% / 84% / 93% | |

**Total produk Indonesia: 9.001** (field `count` pada search `countries_tags_en=indonesia` dan `countries_tags=en:indonesia`, keduanya sama; `q1_v2_search_sample.json`, `q12_search_ctags.json`). Total seluruh OFF: 4.788.440 (`count` pada search tanpa filter di `world`, `q12_search_nofilter_world.json`). Angka diambil 2 Oktober 2026 dan berubah tiap hari. Status: Terverifikasi.

**Populasi: seluruh 8.186 produk Indonesia di dump CSV** (tanpa bias popularitas). Status: Terverifikasi.

| Data | Terisi dan bisa diperingkat |
|------|-----------------------------|
| Nutri-Score a sampai e | **437 (5,3%)**; 7.644 `unknown`, 49 `not-applicable`, 56 kosong |
| Skor lingkungan a-plus sampai f | **341 (4,2%)**; 5.332 `unknown`, 36 `not-applicable`, 2.477 kosong |
| `nova_group` | 382 (4,7%) |
| Tujuh nutrien lengkap | 163 (2,0%); minimal 6 dari 7: 298 (3,6%) |
| Per nutrien | energi 4,7%, protein 4,6%, lemak 4,7%, lemak jenuh 3,7%, gula 4,1%, serat 2,4%, garam 4,0% |
| Asal (`origins_tags` atau `manufacturing_places`) | 341 (4,2%): `origins_tags` 3,5%, `manufacturing_places` 2,4% |
| `packaging_tags` | 286 (3,5%) |
| URL gambar | 6.886 (84,1%) |
| Berlabel `en:halal` | 1.988 (24,3%) |
| `brands` / `product_name` | 39,5% / 93,4% |

**Kecukupan data untuk tabel pembanding.** Diukur dengan metrik kelengkapan data: jumlah dari 6 baris yang terisi (Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama; gizi utama = minimal 6 dari 7 nutrien).

| Baris terisi | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|--------------|---|---|---|---|---|---|---|
| Produk | 7.301 | 365 | 173 | 151 | 101 | 53 | 42 |

Kumulatif: minimal 4 baris **196 produk (2,4%)**, 194 di antaranya bergambar; minimal 5 baris 95; minimal 3 baris 347; minimal 2 baris 520. Sebanyak 5.987 produk punya nama dan gambar tetapi paling banyak satu baris terisi. Mereka bahan antrean Modul 4.

**Dampak:**
- Target minimum 50 produk **tidak terlanggar**: 196 produk punya data cukup. Tetapi target kerja 150 sampai 200 produk hampir menghabiskan seluruh stok yang layak.
- Katalog yang diisi dari seluruh produk Indonesia akan didominasi produk tanpa data. Target kelengkapan 70% hanya tercapai bila seeding memilih produk dengan minimal 4 baris.
- Asumsi 1 di rencana proyek ("OFF punya cukup produk pasar Indonesia") benar untuk jumlah (8.186 sampai 9.001) tetapi salah untuk kelengkapan. Asumsi 2 ("Nutri-Score lebih lengkap dibanding Green-Score") benar secara angka (5,3% vs 4,2%), tetapi selisihnya kecil dan tidak relevan bagi pengguna.

Sampel API 100 produk populer (tabel pertama di atas) hanya untuk perbandingan: ia condong ke produk populer, dan 50 sampai 54 dari 100 produknya punya minimal 4 dari 6 baris. Rincian di `q1_v2_search_sample.json`.

## Q2. Nilai grade

**Nilai yang teramati (100 produk, v2):**

| Field | Nilai |
|-------|-------|
| `nutrition_grades` dan `nutriscore_grade` | `a`, `b`, `c`, `d`, `e`, `unknown`, `not-applicable`. Kedua field identik pada 100 dari 100 produk |
| `ecoscore_grade` | `a`, `b`, `c`, `d`, `e`, **`f`** (2 produk), `unknown`, `not-applicable` |
| `environmental_score_grade` | tidak pernah muncul |
| `nova_group` | angka 1 sampai 4, atau key tidak ada |

**Nilai di seluruh 8.186 produk Indonesia (dump CSV).** `nutriscore_grade`: `a`, `b`, `c`, `d`, `e`, `unknown`, `not-applicable`, atau kosong (56 produk). `environmental_score_grade`: `a-plus` (**8 produk**), `a`, `b`, `c`, `d`, `e`, `f` (11), `unknown`, `not-applicable`, atau kosong (2.477). Sel kosong di CSV berarti "tidak ada nilai", bukan `"unknown"`. Terverifikasi (`run_check_off_encodings_csv.txt`). Kode server memuat daftar yang sama: `'a-plus', 'a', 'b', 'c', 'd', 'e', 'f', 'not-applicable', 'unknown'` (`lib/ProductOpener/Display.pm:2385`). Dampak: `choices` untuk skor lingkungan harus memuat `a-plus` dan `f`; Nutri-Score tidak punya keduanya. Satu aturan membaca grade dari dump dan dari API: sel kosong, key tidak ada, `unknown`, dan `not-applicable` sama-sama "tidak bisa diperingkat".

**Nama field berbeda antara dump dan API.** Dump CSV hanya punya `environmental_score_grade` (dan `environmental_score_score`), tanpa `ecoscore_grade` (0 dari 8.186). API v2 dan v3 kebalikannya (lihat di bawah). Kode pembaca grade tetap membaca nama baru lebih dulu dengan cadangan nama lama, sehingga satu fungsi melayani kedua sumber. Terverifikasi.

**v2 dan v3:** keduanya mengembalikan `ecoscore_grade`, `ecoscore_score`, `ecoscore_data`, `nutriscore_grade`, `nutrition_grades`, dan tidak mengembalikan `environmental_score_grade`. Terverifikasi untuk Indomie Mi Goreng tanpa parameter `fields` (267 key di v2 dan v3, tanpa `environmental_score_*`) dan dengan `fields` yang meminta kedua nama (`q2_v3_indomie_envfields.json`), serta untuk 100 produk search v2. Ketergantungan pada `fields` dan subdomain: tidak ada. Hasilnya sama di `id`, `world`, dan `cc=fr`.

**Dokumentasi bertentangan dengan respons.** Changelog menyebut API v3.1 (12 Des 2024, produk versi 1000) mengganti `ecoscore_*` menjadi `environmental_score_*` (https://openfoodfacts.github.io/openfoodfacts-server/api/ref-api-and-product-schema-change-log/). Versi v3 terbaru di changelog adalah 3.6 (27 Mei 2026). Respons langsung masih memakai nama lama, dan Indomie yang diuji punya `schema_version` 999, di bawah 1000. Dugaan: produk yang belum disimpan ulang setelah skema 1000 masih memakai nama lama, sementara produk yang baru diubah sudah memakai nama baru. Dugaan ini belum terbukti: 0 dari 101 produk teruji punya nama baru. Kode PilihYuk tetap membaca `environmental_score_grade` lebih dulu dan `ecoscore_grade` sebagai cadangan, seperti rencana awal.

`nutriscore_grade` ada di v2 dan v3 dan nilainya sama dengan `nutrition_grades`. Dampak: baca `nutriscore_grade` (nama baru) dengan cadangan `nutrition_grades`, pola yang sama dengan skor lingkungan. Bukti: `q12_v3_id_nutella.json`, `q2_v3_indomie_envfields.json`.

## Q3. Skor lingkungan per negara

- Grade tingkat atas tidak berubah menurut subdomain atau `cc`: Indomie `a`, skor 75 di `id`, `world`, dan `cc=fr` (`q3_v3_indomie_*.json`). Terverifikasi.
- Ada skor per negara: `ecoscore_data.grades` dan `ecoscore_data.scores` berisi **63 negara**. Kunci `id` **tidak ada**, kunci `world` dan `fr` ada. Terverifikasi (`q3_v3_indomie_id.json`).
- Kode server memakai `scores[cc]` kalau ada, dan kalau tidak ada memakai `world` (`lib/ProductOpener/EnvironmentalScore.pm:1915-1918`). Nilai bawaan yang tersimpan diambil dari `fr` (`EnvironmentalScore.pm:1005-1009`). Status: Terverifikasi dari kode.
- **Yang ditampilkan untuk pengguna Indonesia:** nilai `ecoscore_grade` tingkat atas apa adanya. Indonesia tidak punya entri sendiri, jadi tidak ada angka yang lebih khas Indonesia untuk diambil. Antarmuka menyebutnya "Green-Score" tanpa mengklaim itu skor khusus Indonesia. Hanya satu produk yang dicek; selisih `grades.world` dan `grades.fr` pada produk lain belum diuji (Dugaan: jarang berbeda).

## Q4. Normalisasi barcode

Fungsi server: `normalize_code` (`lib/ProductOpener/Products.pm:470`), `normalize_code_with_gs1_ai` (`:580-606`), `normalize_code_zeroes` (`:493-514`). Aturannya:

1. Ambil digit saja.
2. Jika 12 digit dan cek digit UPC-A benar, tambah satu `0` di depan.
3. Jika 14 digit dan berawalan `0`, buang nol itu.
4. Buang semua nol di depan, isi nol sampai 13 digit.
5. Jika hasil 13 digit berawalan `00000`, potong jadi EAN-8.
6. Kode GS1 (string AI atau digital link) diurai lebih dulu oleh server. `normalize_barcode()` tidak mengurainya.

Dokumentasi (https://openfoodfacts.github.io/openfoodfacts-server/api/ref-barcode-normalization/) hanya menyebut tiga aturan panjang (7 digit ke bawah jadi 8, 9 sampai 12 jadi 13, 13 ke atas tetap) dan menyebut EAN-14 tanpa merinci. Kode lebih lengkap.

Uji langsung:

| Input | Hasil | Bukti |
|-------|-------|-------|
| `089686010947` (12) | `code: 0089686010947` | `q3_v3_indomie_id.json` |
| `03017620422003` (14, awalan 0) | `code: 3017620422003`, peringatan `different_normalized_product_code` | `q4_v3_14digit.json` |
| `0000000000017` | dinormalisasi ke `00000017` (EAN-8) | `q8_v3_notfound.json` |
| `96385074` (8) | tetap 8 digit, produk tidak ada (404) | `q4_v3_7digit.json` |

**Panjang kode di 8.186 produk Indonesia** (dump CSV): 13 digit 7.806, 8 digit 357, 14 digit 17, dan 6 kode non-GTIN (15 digit 1, 17 digit 3, 22 digit 1, 35 digit 1). Terverifikasi. Keputusan kelompok: `Product.code` `max_length=14`, kode lebih panjang dilewati saat seeding dan ditolak di lookup.

Fungsi `normalize_barcode()` ada di `tools/check_off_encodings.py` dengan tes `assert` (`python tools/check_off_encodings.py --selftest`). Kasus 13 digit dan 14 digit tanpa nol di depan hanya diuji lewat `assert` yang meniru kode, belum lewat respons API. Dampak: satu fungsi dipakai di lookup sebelum mencari di katalog lokal. `Product.code` tetap diisi dari `code` respons.

## Q5. `nutriments`

- **Nilai kosong: key tidak ada (API) atau sel kosong (CSV).** Di API, dari 100 produk ada 0 nilai `null` dan 0 string pada tujuh key (`q1_v2_search_sample.json`); 6 produk bahkan tidak punya objek `nutriments`. Di dump CSV, nilai kosong berupa sel kosong, dan `iter_csv` memetakannya ke key yang tidak ada (`run_check_off_encodings_csv.txt`: `absent` untuk 7.802 dari 8.186 produk pada energi). Nilai `0` sah (5 produk bergaram 0 di sampel API), jadi `NULL` dan `0` berbeda. Terverifikasi.
- **Energi.** `energy-kcal_100g` untuk kkal dan `energy-kj_100g` untuk kJ. `energy_100g` selalu kJ (sama dengan `energy-kj_100g` pada 67 produk). Pada sampel tidak ada produk yang punya kJ tanpa kkal. Terverifikasi.
- **Garam dan natrium.** Dua key terpisah, `salt_100g` dan `sodium_100g`. Tidak ada produk yang punya natrium tanpa garam di sampel. Terverifikasi.
- **Sufiks.**

| Sufiks | Arti | Pada sampel |
|--------|------|-------------|
| `_100g` | nilai per 100 g atau 100 ml dalam satuan dasar | dipakai aplikasi |
| `_serving` | nilai per sajian | 86 dari 100 produk |
| `_prepared_100g` | nilai per 100 g setelah disiapkan (mi setelah direbus) | 4 dari 100 produk |
| `_modifier` | penanda, nilainya `"~"` (perkiraan) | 139 kemunculan, 1 pada ketujuh nutrien |
| `_unit`, `_value` | satuan asal dan nilai asal sebelum konversi | ada |

- Nilai per 100 g hasil konversi dari per sajian bisa berekor panjang: 179 dari paling banyak 700 nilai (7 key kali 100 produk) punya lebih dari 4 desimal. `FloatField` dan pembulatan tampilan tetap benar.

**Key per kolom Product** (nama kolom Django di kiri, key OFF di kanan). Dua key memakai tanda hubung, bukan garis bawah:

| Kolom Product | Key `nutriments` |
|---------------|------------------|
| `energy_kcal_100g` | `energy-kcal_100g` |
| `proteins_100g` | `proteins_100g` |
| `fat_100g` | `fat_100g` |
| `saturated_fat_100g` | `saturated-fat_100g` |
| `sugars_100g` | `sugars_100g` |
| `fiber_100g` | `fiber_100g` |
| `salt_100g` | `salt_100g` |

## Q6. Bahasa

- **Nama produk.** `product_name_id` terisi pada 43 dari 100 produk, `product_name` pada 96, `product_name_en` pada 77. Bahasa produk (`lang`): `en` 51, `id` 26, `fr` 19. Terverifikasi. Nama berbahasa Indonesia sering tidak ada, dan `product_name` sering berbahasa Inggris atau Prancis karena produknya memang dilabeli begitu.
- **Parameter bahasa.** Subdomain `id` mengubah teks status respons ke Indonesia (`"lc_name": "Produk ditemukan"`, `q12_v3_id_nutella.json`), tetapi isi data produk tidak berubah. Parameter `lc` dan `tags_lc` tidak diuji (Dokumentasi: `lc` dan `cc` muncul di endpoint taxonomy pada ref-cheatsheet). Dugaan: tidak mengubah nama produk.
- **Taxonomy.** `categories.json` (4,7 MB) dan `labels.json` (1,2 MB) di `https://static.openfoodfacts.org/data/taxonomies/` punya nama bahasa Indonesia untuk **109 dari 14.717 kategori (1%)** dan **7 dari 3.074 label (0%)**. `en:halal` tidak punya nama Indonesia. Pada sampel, 23% pemakaian tag kategori dan 3% pemakaian tag label punya terjemahan. Terverifikasi. Dampak: antarmuka butuh peta terjemahan sendiri untuk kategori dan label yang dipakai katalog, dengan cadangan ke nama Inggris. Endpoint `/api/v2/taxonomy` yang dicoba lewat tebakan mengembalikan `{}` sehingga tidak dipakai.

Rekomendasi nama: `product_name_id` kalau ada, lalu `product_name`, lalu `product_name_en`. Satu kolom `product_name` di Product, diisi dengan aturan itu saat seeding.

## Q7. Gambar dan lisensi

- **Field stabil.** `image_url` sama persis dengan `image_front_url` pada 98 dari 98 produk bergambar, jadi cukup satu. `selected_images.front.display`/`small`/`thumb` memberi URL per bahasa. Semua URL memuat nomor revisi (`front_it.69.400.jpg`), jadi URL berubah bila gambar diganti dan refresh perlu memperbarui `image_url`. Terverifikasi.
- **Ukuran.** 100 (`thumb`), 200 (`small`), 400 (`display`), dan ukuran penuh. `image_url` berukuran 400, `image_front_small_url` 200. Terverifikasi (`q1_v2_search_sample.json`); ukuran penuh terlihat di metadata Parquet (`images.sizes.full`).
- **Lisensi (Dokumentasi, https://world.openfoodfacts.org/terms-of-use dan https://id.openfoodfacts.org/data):**
  - Struktur basis data: ODbL. Isi: DbCL. Gambar: CC BY-SA 3.0.
  - Pengguna ulang wajib menyebut lisensi dan menyatakan Open Food Facts sebagai sumber, dengan tautan ke https://openfoodfacts.org, versi lokalnya, atau halaman produk bila datanya tentang produk tertentu.
  - Turunan wajib dibagikan dengan syarat yang sama. Hak pihak ketiga (merek dagang, desain kemasan) menjadi tanggung jawab pengguna ulang.
  - Dokumen tidak merinci tampilan wajib di aplikasi.
- **Yang wajib tampil di PilihYuk (Dugaan, tafsir dari kutipan di atas):** satu kalimat atribusi di footer (`footer.html`), "Data dari Open Food Facts (ODbL), gambar CC BY-SA", dengan tautan ke openfoodfacts.org, ditambah tautan ke halaman produk OFF di halaman detail. Koreksi lokal dari kurator membuat data kita turunan, jadi lisensi dan sumber disebut juga di dokumentasi repo. Perlu dikonfirmasi ke asisten dosen bila dinilai.

## Q8. Error

- **Produk tidak ada (v3).** HTTP **404** dengan badan JSON: `status: "failure"`, `result.id: "product_not_found"`, plus `errors` berisi `invalid_code` (kode awal) dan `product_not_found` (kode ternormalisasi) (`q8_v3_notfound.json`). Dokumentasi mengonfirmasi 404 (changelog, produk versi 996). Terverifikasi.
- **503.** Terjadi **acak**: request yang sama gagal lalu sukses beberapa detik kemudian. Search v2 membalas 503 pada kira-kira separuh percobaan, sedangkan baca produk v3 selalu 200 (atau 404 untuk produk tidak ada). Badan respons 503 adalah **halaman HTML** ("Page temporarily unavailable", `Content-Type: text/html`), bukan JSON, jadi klien yang langsung memanggil `.json()` akan gagal. Terverifikasi. Skrip diberi retry (jeda 15, 30, 60 detik); `run_check_off_encodings.txt` mencatat 3 kali 503 lalu sukses (21 kali 200).
- **429.** Tidak tercantum di dokumentasi OFF. Dokumen menyebut **503** untuk pelampauan batas global (`docs/api/index.md:60`). 429 tidak dipicu karena itu melanggar aturan rate limit. SDK Dart menangani 429 (`TooManyRequestsException`). Status: Dokumentasi untuk 503; 429 tidak diketahui.
- **Rate limit resmi per IP** (https://openfoodfacts.github.io/openfoodfacts-server/api/, `docs/api/index.md:45-60`): **15 req/menit** untuk baca produk, **10 req/menit** untuk search. Ada juga batas global tanpa memandang IP; bila lewat, 503. Bila request berasal langsung dari pengguna (aplikasi ponsel), batas berlaku per pengguna. Status: Dokumentasi.
- **Timeout.** SDK Python memakai 10 detik (`openfoodfacts-python/src/openfoodfacts/types.py:863`). Waktu respons teramati 0,7 sampai 1,1 detik. Rekomendasi: 10 detik, dua kali retry dengan jeda bertambah, hanya untuk 5xx dan kegagalan jaringan. Status: Dugaan.

## Q9. Search

- **Dokumentasi menyarankan** v3 untuk integrasi baru, `/api/v2/search` tetap bekerja walau v2 ditandai deprecated, dan **Search-a-licious** (`https://search.openfoodfacts.org`) untuk pencarian teks (Dokumentasi: halaman utama API). Search-a-licious tidak diuji. `search_terms` dan `cgi/search.pl` adalah jalur lama.
- **Larangan ekstraksi:** "search is not a good way to extract info from the database, and anyone trying to do that will be rate-limited and banned" (`docs/api/tutorials/finding-healthy-cereals.md:5`). Jadi search tidak dipakai untuk menyalin katalog.
- **Paginasi (Terverifikasi).** `page` dan `page_size` bekerja; `count`, `page`, `page_count`, `page_size`, `skip` ada di respons. **`page_size` maksimum 100**: `page_size=1000` dijawab `page_size: 100` (`q9_ps1000.json`). `page=2` dengan `page_size=3` mengembalikan `skip: 3` (`q9_page2_sort.json`).
- **Sort.** `sort_by=unique_scans_n` dan `sort_by=last_modified_t` diterima. Urutan bawaan sama dengan `unique_scans_n` (populer dulu). Nilai `sort_by` lain tidak diuji.
- **Filter negara.** `countries_tags_en=indonesia` dan `countries_tags=en:indonesia` sama-sama bekerja (lihat Q12).

## Q10. `misc_tags`

Arti tag dibaca dari kode server; frekuensi dari 100 produk (`q1_v2_search_sample.json`).

| Tag | Arti | Sumber kode | Pada sampel |
|-----|------|-------------|-------------|
| `en:nutriscore-not-computed` | Nutri-Score tidak bisa dihitung | `Food.pm:1913` | 33 |
| `en:nutriscore-computed` | Nutri-Score berhasil dihitung | | 67 |
| `en:nutriscore-missing-nutrition-data` | Ada nutrien yang kosong | `Food.pm:1712`, `:1783` | 19 |
| `en:nutriscore-missing-nutrition-data-<nutrien>` | Nutrien tertentu kosong (misalnya `-sodium`) | `Food.pm:1713` | 17 untuk natrium |
| `en:nutriscore-missing-fiber` | Serat kosong | | 21 |
| `en:nutriscore-missing-prepared-nutrition-data` | Butuh gizi setelah disiapkan | `Food.pm:1669` | belum dipakai di aplikasi |
| `en:nutrition-data-per-100g` / `en:nutrition-data-per-serving` | Gizi di kemasan per 100 g atau per sajian | | 39 / 43 |
| `en:environmental-score-not-computed` | Green-Score tidak bisa dihitung | `EnvironmentalScore.pm:891`, `:1056` | 43 |
| `en:environmental-score-computed` | Green-Score berhasil dihitung | | 55 |
| `en:environmental-score-missing-data-packagings` | Data kemasan kurang | `EnvironmentalScore.pm:1035` | 45 |
| `en:environmental-score-missing-data-origins` | Asal bahan kurang | | 34 |
| `en:environmental-score-missing-data-labels` | Label kurang | | 55 |
| `en:packagings-complete` / `en:packagings-not-complete` / `en:packagings-empty` | Kelengkapan data kemasan | `Packaging.pm:836`, `:840`, `:843` | tidak dihitung / 93 / 51 |
| `en:packagings-not-empty-but-not-complete` | Kemasan terisi tapi belum lengkap | | 42 |

Tag `nutriscore-*`, `environmental-score-*`, dan `packagings-*` cukup untuk deteksi kelengkapan di Modul 4. Dua tag khusus Indonesia: `en:main-countries-id-product-name-not-in-country-language` (42) dan `en:main-countries-id-no-data-in-country-language` (39). Arti keduanya (data belum berbahasa Indonesia) dibaca dari namanya, bukan dari kode. Status: Dugaan.

## Q11. Ekspor dan dump

Ukuran diukur dengan `HEAD` pada 2 Oktober 2026 (tidak ada file yang diunduh). Semua file **global**; tidak ada ekspor per negara. Status: Terverifikasi.

| Format | URL | Ukuran | Pembaruan |
|--------|-----|--------|-----------|
| JSONL gz | `static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz` | **13,06 GB** | harian |
| Parquet | `huggingface.co/datasets/openfoodfacts/product-database/resolve/main/food.parquet` | **7,87 GB** | harian |
| CSV gz (tab) | `static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz` | **1,28 GB** (sekitar 9 GB terurai menurut halaman data) | harian |
| MongoDB dump | `static.openfoodfacts.org/data/openfoodfacts-mongodbdump.gz` | tidak diukur | malam hari |
| Delta JSON | `static.openfoodfacts.org/data/delta/index.txt` | tidak diukur | harian, simpan 14 hari |

Semuanya melewati batas 500 MB. Atas izin pemilik proyek, hanya **CSV (1,28 GB)** yang diunduh, ke direktori sementara di luar proyek. File lain tidak diunduh.

**Cara menyaring di laptop.**

| Cara | Data yang dibaca | Waktu | Status |
|------|------------------|-------|--------|
| **Streaming CSV gz dengan Python (`iter_csv` di skrip), tanpa dependency** | 1.275.171.186 byte | Unduh **148 detik** (sekitar 8,6 MB/s); streaming 4.535.553 baris dan menyaring **52 detik** | **Terukur** |
| Streaming JSONL dengan Python (`iter_dump`) | 13,06 GB, gunzip berurutan | Belum diukur. Kasar: unduhan sekitar 25 menit pada kecepatan yang sama, parse JSON per baris beberapa kali lebih lambat dari CSV | Dugaan |
| DuckDB pada Parquet jarak jauh | Hanya kolom yang dibutuhkan, lewat HTTP range | Footer terbaca 11,5 detik; sisanya belum diukur | Footer terukur, sisanya Dugaan |

Dua kekurangan CSV: **tidak ada kolom `misc_tags` dan `product_name_id`**, dan nama kolom skor lingkungan `environmental_score_grade` (bukan `ecoscore_grade`). CSV punya `states_tags` (misalnya `en:origins-to-be-completed`) sebagai pengganti kasar untuk deteksi kelengkapan, tetapi deteksi data kosong di Modul 4 memakai `misc_tags`. Dump CSV juga dibuat 1 Okt 2026 12:25 GMT dan memuat **8.186** produk Indonesia, sedangkan API menghitung **9.001** sehari kemudian. Penyebab selisih belum diketahui (Dugaan: ekspor CSV mengecualikan sebagian produk).

**Ukuran kolom Parquet yang relevan** (dijumlah dari metadata footer, `parquet_metadata()`): `countries_tags` 7,1 MB; `code` 58 MB; `nutriscore_grade` 2,2 MB; `environmental_score_grade` 2,6 MB; `nova_group` 1,4 MB; `origins_tags` 3,3 MB; `misc_tags` 49 MB. Memilih produk Indonesia beserta kriteria kelengkapan perlu sekitar 125 MB. Kolom lengkap yang dipakai aplikasi, termasuk `nutriments` (sekitar 330 MB) dan nama produk (109 MB), berjumlah sekitar 700 MB bila seluruh baris dibaca. Karena baris Indonesia tersebar di banyak row group, byte yang ditransfer untuk 200 baris belum diukur. Status: ukuran kolom Terverifikasi, total byte yang ditransfer Dugaan.

**Field penyaring.** `countries_tags`, nilai `en:indonesia`. Terverifikasi di CSV (kolom `countries_tags`, isi dipisah koma, dipakai `iter_csv`) dan di Parquet (`countries_tags, list, element` pada metadata). Di JSONL nama field sama (`iter_dump` memakainya, belum dijalankan pada dump sungguhan).

**Jalur seeding yang dipilih (keputusan kelompok): CSV, produk dengan minimal 4 dari 6 baris pembanding (±194 produk).**
1. `iter_csv()` menyaring baris Indonesia (`is_indonesian()`), membuang kode bukan GTIN (lebih dari 14 digit), dan memilih produk yang minimal 4 dari 6 barisnya terisi. Satu kali jalan, 52 detik setelah unduhan. Dijalankan satu orang; CSV 1,28 GB tidak masuk repositori.
2. Hasilnya ditulis menjadi fixture Django. Hanya fixture yang di-commit.
3. Yang tidak ada di CSV (`misc_tags`, `product_name_id`) diisi lewat satu kali pembacaan v3 per barcode, 4,5 detik per request, sekitar 15 menit untuk 194 produk, atau dibiarkan kosong sampai refresh pertama. Ini opsional, karena `misc_tags` dibutuhkan Modul 4 tetapi hanya untuk produk yang masih punya data kosong.

Dibandingkan sampel search: tidak ada pagination 100 produk per request, tidak bias popularitas, dan tidak memanggil API produksi untuk menyalin katalog (dilarang di `docs/api/tutorials/finding-healthy-cereals.md:5`). Parquet jarak jauh dan JSONL tidak dipakai.

## Q12. Filter Indonesia

- **Baca produk v3 lewat `id.openfoodfacts.org` TIDAK menyaring.** Barcode Nutella `3017620422003` di `id` mengembalikan produk dengan `countries_tags: ["en:france"]` (`q12_v3_id_nutella.json`), identik dengan di `world`. Terverifikasi. Konsekuensi: asumsi awal ("runtime memakai subdomain id agar hasil tersaring") salah untuk lookup barcode dan refresh. README sudah dikoreksi.
- **Search v2 di `id` menyaring otomatis.** Tanpa parameter negara: `count` 9.001 dan 50 dari 50 produk punya `en:indonesia`. Di `world`: `count` 4.788.440 dan 0 dari 50 (`q12_search_nofilter_id.json`, `q12_search_nofilter_world.json`). Terverifikasi.
- **Parameter filter negara di search v2:** `countries_tags_en=indonesia` dan `countries_tags=en:indonesia` sama-sama menghasilkan `count` 9.001 dan semua produk `en:indonesia` (`q12_search_ctags.json`, `q1_v2_search_sample.json`). Keduanya Terverifikasi; dokumen yang dibaca tidak menyebut mana yang "resmi".
- **Kolom dump:** `countries_tags`, nilai `en:indonesia`.
- **`is_indonesian(product)`** ada di `tools/check_off_encodings.py` dengan tes `assert`. Satu aturan: `isinstance(countries_tags, list) and "en:indonesia" in countries_tags`. Field hilang atau bukan daftar dianggap bukan Indonesia. Dipakai di seeding, lookup barcode, dan refresh, dan tidak bergantung pada subdomain.
- **Produk dengan data cukup untuk tabel pembanding:** 196 dari 8.186 (2,4%), detail di Q1. Stok layak nyaris sama dengan target kerja 150 sampai 200, jadi seeding harus memilih produk dengan minimal 4 baris.
- **Kasus pinggir:** data Indonesia di OFF belum lengkap, jadi produk yang sebenarnya dijual di Indonesia bisa belum berlabel (README, Latar Belakang). Penanganannya: jalur tambah manual di Modul 1 untuk produk yang belum berlabel.

## Q13. Halaman detail: bahan, alergen, porsi, natrium (tambahan setelah wireframe)

Wireframe Detail Produk memuat teks bahan, chip alergen, berat bersih, dan jumlah porsi. Pengecekan di API v3 untuk Indomie Mi Goreng (`k18_v3_indomie_ingredients.json`) dan di dump CSV (8.186 produk Indonesia). Status: Terverifikasi.

| Data | Ada di OFF? | Seluruh produk Indonesia | 196 produk yang di-seed |
|------|-------------|--------------------------|-------------------------|
| Teks bahan | Ya: `ingredients_text`, dan per bahasa (`ingredients_text_id`) | 1.510 (18,4%) | 191 (97,4%) |
| Alergen | Ya: `allergens_tags` di API. Dump CSV tidak punya kolom itu, hanya `allergens` berupa teks tag, kadang bercampur teks bebas (`id:Asam askorbat`) | 159 (1,9%) | 107 (54,6%) |
| Berat bersih | Ya: `quantity` (`85 g`), `product_quantity` (85) | 4.018 (49,1%) | 193 (98,5%) |
| Ukuran porsi | Ya: `serving_size` (`85 g`), `serving_quantity` (85) | 1.531 (18,7%) | 185 (94,4%) |
| Jumlah porsi | Bukan field; bisa dihitung dari berat bersih dan ukuran porsi | | |
| Dapat didaur ulang | Tidak ada sebagai field produk | | |

Produk yang di-seed (minimal 4 dari 6 baris pembanding) hampir selalu punya bahan dan porsi, karena produk yang gizinya lengkap biasanya dimasukkan kontributor dengan foto kemasan lengkap. Produk lain jarang punya keduanya. Dampak: halaman detail bisa memakai data OFF tanpa input manual; Product bertambah `ingredients_text`, `allergens`, `serving_size`.

**Natrium dan karbohidrat.** Di API, `sodium_100g` bernilai 0,3976 dan `carbohydrates_100g` 64,7059 untuk Indomie Mi Goreng. Natrium dalam gram (tampil 398 mg). Di dump CSV kolom `sodium_100g` terisi 324 produk (4,0%) dan `carbohydrates_100g` 382 (4,7%).

