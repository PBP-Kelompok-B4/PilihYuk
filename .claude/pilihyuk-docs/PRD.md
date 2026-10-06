# Product Requirements Document (Sementara)

**Produk:** PilihYuk, pembanding gizi dan dampak lingkungan makanan dan minuman per shelf
**Konteks:** Proyek Tengah Semester, Pemrograman Berbasis Platform (CSGE602022), Fasilkom UI, Gasal 2026/2027
**Kelompok:** 4, Kelas B
**Sub-tema:** Sustainable Food & Diet
**Versi:** 0.4, 4 Oktober 2026 (diperbarui 6 Oktober)
**Status:** draf kerja. README adalah sumber kebenaran untuk pembagian modul. Bukti verifikasi API ada di `.claude/pilihyuk-docs/off-api-findings.md` dan `off-sdk-evaluation.md`. Keputusan ada di bagian 13: butir yang sudah diambil telah disetujui kelompok dan pemilik modul (seeding, butir 16, dibahas lagi nanti), dan yang belum diambil punya usulan bawaan.

---

## Riwayat versi

**v0.4 (4 Oktober 2026).** Autentikasi selesai dua hari lebih awal (F-0.1 sampai F-0.10, NF-11, keputusan 38 sampai 42): login dengan email di atas `User` bawaan, sedangkan verifikasi email, reset password, dan masuk dengan Google ditunda. `SECRET_KEY` wajib dari environment, `django~=5.2.0` dan `django-axes` masuk `requirements.txt`, dan `Procfile` menjalankan migrasi saat rilis. Bagian 11 dan 14 bertambah butir untuk hal ini.

**v0.3.**
- **Hanya produk Indonesia.** Website hanya memuat produk yang dijual di Indonesia (`countries_tags` memuat `en:indonesia`), dicek satu fungsi `is_sold_in_indonesia()` di seeding, lookup barcode, dan refresh (bagian 5, F-1.4, F-1.7).
- **Koreksi sumber data.** Subdomain `id` tidak menyaring pembacaan v3. Cakupan jauh lebih rendah dari dugaan: hanya 196 dari 8.186 produk punya minimal 4 dari 6 baris pembanding. Seeding pindah ke dump CSV dengan seleksi itu. Key gizi memakai tanda hubung, grade lingkungan bisa `a-plus` dan `f`, dan nama field skor lingkungan berbeda antara API dan dump (bagian 5, 7, 10, 11).
- **Keputusan K-1 sampai K-6 dijawab**, dan model data berubah: `Product` bertambah `is_active` dan `halal_labeled`, `code` dibatasi 14 karakter, dan ada entitas baru `ProductView`, `SavedShelf`, serta `DataCorrectionItem` (bagian 7, 13).
- **Wireframe Figma dibaca.** Tabel pembanding memuat maksimal 4 produk (F-2.14), `salt_100g` diganti `sodium_100g` dan `carbohydrates_100g` ditambah, `Product` bertambah `ingredients_text`, `allergens`, dan `serving_size`, dan framework CSS adalah Tailwind (keputusan 28). Simpan shelf menggantikan fork shelf (F-2.12, F-2.13). Modul 4 berubah: satu pengajuan boleh memuat beberapa field dan ditinjau per field (F-4.1 sampai F-4.5).
- **Aturan filter berubah** dari data Public/mock API menjadi data database. Butir "Filter API" di README menjadi "Filter database" (bagian 6, F-1.2, F-1.7, F-2.11, F-3.7, F-4.7).
- **Kerangka kode.** Enam app Django terdaftar, template dan JavaScript kosong disiapkan per app, dan halaman landing dibuat agar mudah beralih ke data asli (keputusan 33 sampai 35). Linimasa di bagian 12 dirinci per minggu.

**v0.2.** Nama aplikasi ditetapkan: PilihYuk. Unit pembanding berganti dari `ComparisonSet` menjadi shelf. Lima modul disusun ulang mengikuti README: `Review` dihapus, Substitusi dan `DataCorrection` jadi modul sendiri, Profil diganti Preferensi Nutrisi dan Riwayat Keputusan, Kandidat Daftar Belanja tidak dipakai. Pengunjung hanya membaca shelf publik. Seeding berganti dari daftar barcode lewat API menjadi dump nightly. Nilai skor kosong ternyata string `"unknown"` atau `"not-applicable"`, bukan `null`. Bagian Model Data ditambahkan (`SubstitutionVote`, constraint unik, kebijakan hapus).

## 1. Masalah

Dua produk di rak yang sama punya perbedaan gizi dan dampak lingkungan yang tidak terlihat dari kemasannya. Label seperti "alami" dan "rendah gula" tidak terstandar dan tidak bisa dibandingkan antar merek. Data yang terstandar memang ada, yaitu Nutri-Score untuk gizi, NOVA untuk tingkat pemrosesan, dan Green-Score untuk dampak lingkungan, tetapi datanya berada di basis data berbahasa Inggris yang tidak dibuka orang ketika sedang berbelanja.

Basis data itu juga disusun per kategori, padahal pilihan di depan rak sering lintas kategori. Orang yang mencari sesuatu untuk dituang ke kopi memilih antara susu UHT, susu bubuk, krimer, dan oat milk, yang di Open Food Facts berada di kategori berbeda.

Akibatnya pembeli yang ingin memilih lebih baik tetap memutuskan berdasarkan harga, merek, dan klaim di kemasan.

## 2. Tujuan Produk

1. Pengguna bisa mengumpulkan produk yang saling menggantikan ke dalam satu shelf dan melihat perbedaannya pada dimensi yang sama dalam satu tabel.
2. Shelf yang sudah dibuat bisa dibuka lagi dan dipakai pengguna lain, sehingga tidak ada yang mengulang pekerjaan yang sama tiap kali belanja.
3. Pengguna bisa menyatakan preferensi nutrisi dua arah, misalnya "maksimalkan protein", dan urutan tabel mengikutinya.
4. Pengguna bisa mengusulkan pengganti produk lintas shelf, dan komunitas menilai usulan itu.
5. Data produk yang keliru atau kosong bisa diperbaiki pengguna, karena basis data sumber tidak lengkap untuk pasar Indonesia. Temuan v0.3 memperkuat alasan ini: 89% produk Indonesia di Open Food Facts tidak punya satu pun baris pembanding yang terisi.

## 3. Bukan Tujuan

Hal berikut sengaja tidak dikerjakan pada versi ini:

- Pemindaian barcode lewat kamera. Barcode tetap bisa diketik manual. Pemindaian lebih cocok untuk aplikasi Flutter di Proyek Akhir Semester.
- Perbandingan harga dan integrasi dengan toko atau marketplace.
- Rekomendasi otomatis berbasis machine learning.
- Pelacakan asupan gizi harian. Produk ini membantu memilih saat membeli, bukan mencatat yang sudah dimakan.
- Saran gizi atau kesehatan. Aplikasi menyaring dan mengurutkan; teks antarmuka tidak boleh terbaca sebagai rekomendasi kesehatan.
- Mengirim koreksi data balik ke Open Food Facts. Koreksi yang disetujui hanya berlaku di basis data lokal.
- Menampilkan produk yang tidak dijual di Indonesia. Produk Open Food Facts tanpa `en:indonesia` di `countries_tags` ditolak (bagian 5).
- Menyalin (fork) shelf. Pengganti yang dikerjakan adalah menyimpan shelf ke "Shelf Saya" (F-2.12).

## 4. Pengguna

| Peran | Deskripsi | Yang bisa dilakukan |
|-------|-----------|---------------------|
| Pengunjung | Belum punya akun, biasanya datang dari pencarian atau tautan shelf | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, membaca usulan substitusi tanpa identitas pengusul |
| Pengguna Terdaftar | Sudah login, akan kembali lagi | Semua di atas, ditambah mengelola shelf, menyimpan shelf ke Shelf Saya, mengusulkan substitusi dan memberi suara, mengajukan koreksi data, mengatur preferensi nutrisi, dan mencatat riwayat keputusan |
| Kurator Data | Pengguna terdaftar dengan `is_staff` bernilai benar | Meninjau pengajuan koreksi, menyetujui atau menolaknya, dan menyunting entri produk manual milik siapa pun |

Kurator memakai field bawaan Django `is_staff`, tanpa model User kustom, untuk menghindari masalah migrasi `AUTH_USER_MODEL`. Wewenang kurator hanya dipakai di dua tempat: antrean tinjauan `DataCorrection` (Modul 4) dan penyuntingan Product manual milik siapa pun (Modul 1). Produk dari Open Food Facts dikoreksi lewat `DataCorrection`, bukan disunting langsung, supaya koreksinya tercatat dan tidak tertimpa refresh (K-2).

Batas antara pengunjung dan pengguna terdaftar memenuhi syarat filter berbasis autentikasi pada spesifikasi tugas.

## 5. Sumber Data

Open Food Facts API, gratis dan tanpa API key untuk operasi baca. Bukti untuk setiap klaim di bagian ini ada di `.claude/pilihyuk-docs/off-api-findings.md` (nomor Q1 sampai Q13).

- Dokumentasi: https://openfoodfacts.github.io/openfoodfacts-server/api/
- Baca satu produk lewat barcode: API v3 di `https://id.openfoodfacts.org/`.
- Pencarian terstruktur: `/api/v2/search`, karena belum tersedia di v3 meski v2 sudah deprecated. Pencarian teks bebas disarankan dokumentasi lewat Search-a-licious (`https://search.openfoodfacts.org`); tidak dipakai dan tidak diuji. Search tidak dipakai untuk menyalin katalog: dokumentasi menyatakan pelakunya akan dibatasi dan diblokir.
- Staging untuk pengembangan: `https://world.openfoodfacts.net/` dengan basic auth `off` / `off`.
- Dump untuk seeding: https://id.openfoodfacts.org/data. Semua ekspor global, tidak ada ekspor per negara. Yang dipakai: CSV (`en.openfoodfacts.org.products.csv.gz`, 1,28 GB). JSONL (13,06 GB) dan Parquet (7,87 GB) tidak dipakai.
- User-Agent: `PilihYuk/0.1 (PBP Fasilkom UI; https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/; https://github.com/pbp-Kelompok-B4/PilihYuk/)` (NF-7).

Field yang dipakai: `code`, `product_name`, `product_name_id`, `brands`, `quantity`, `image_url`, `nutriscore_grade` (cadangan `nutrition_grades`), `nova_group`, `categories_tags`, `labels_tags`, `countries_tags`, `origins_tags`, `manufacturing_places`, `packaging_tags`, `ingredients_analysis_tags`, `ingredients_text`, `allergens_tags`, `serving_size`, `nutriments`, `misc_tags`, dan skor lingkungan (`environmental_score_grade`, cadangan `ecoscore_grade`).

### Aturan: hanya produk Indonesia

Website hanya memuat produk yang **dijual di Indonesia**, yaitu produk yang `countries_tags`-nya berisi `en:indonesia`. Ini bukan soal negara asal produksi. Produk impor yang dijual di Indonesia termasuk. Produk buatan Indonesia yang hanya dijual di luar negeri tidak. Asal produk tetap diambil dari `origins_tags` dan `manufacturing_places` untuk filter "negara asal" di Modul 1.

Aturan ini dijalankan satu fungsi, `is_sold_in_indonesia(product)`, yang disiapkan di `product_catalog/open_food_facts.py` beserta tesnya (diserahkan ke Yasmin untuk di-commit di modulnya) (sebelumnya bernama `is_indonesian()` di skrip riset `.claude/pilihyuk-docs/tools/check_off_encodings.py`). Fungsi itu mengembalikan benar bila `countries_tags` berupa daftar yang memuat `en:indonesia`, dan salah bila field hilang atau bukan daftar. Hasilnya tidak bergantung pada subdomain yang dipakai. Fungsi yang sama berlaku di tiga jalur:

| Jalur | Perilaku |
|-------|----------|
| Seeding dari dump | Baris tanpa `en:indonesia` dilewati |
| Lookup barcode saat runtime | Produk Open Food Facts yang bukan Indonesia **ditolak** dengan pesan yang menjelaskan alasannya dan menawarkan jalur tambah manual (F-1.4). Tidak ada penyimpanan sama sekali |
| Refresh satu produk | Jika label `en:indonesia` hilang di Open Food Facts, data lokal tidak ditimpa dan produk tidak dihapus. Produk dilewati dan `last_synced_at` tidak berubah |

Produk `source=manual` dianggap produk Indonesia karena pengguna yang menyatakannya, dan tidak pernah di-refresh (K-2). Pertimbangannya: data Indonesia di Open Food Facts belum lengkap, jadi produk yang sebenarnya dijual di Indonesia bisa belum berlabel. Jalur manual menampungnya tanpa membuat aturan ini tidak bisa diuji.

### Dua jalur data

- **Seeding awal** dari dump CSV, disaring dengan `is_sold_in_indonesia()`, dibatasi pada produk yang minimal 4 dari 6 baris pembanding terisi (lihat cakupan di bawah), lalu diekspor jadi fixture Django. Hanya fixture yang masuk repositori. Kode lebih dari 14 digit dilewati. Dump tidak punya `misc_tags` dan `product_name_id`, jadi dua field itu dilengkapi lewat satu kali pembacaan v3 per barcode atau menunggu refresh pertama (K-12).
- **Runtime** hanya untuk mencari barcode yang belum ada di katalog dan menyegarkan data satu produk, lewat `product_catalog/open_food_facts.py`, klien `requests` tipis (bukan SDK, lihat `.claude/pilihyuk-docs/off-sdk-evaluation.md`). Barcode dinormalisasi dengan `normalize_barcode()`, lalu produk yang diterima diperiksa dengan `is_sold_in_indonesia()`.

Batasan sumber data yang memengaruhi rancangan. Bukti dan angka lengkapnya ada di `.claude/pilihyuk-docs/off-api-findings.md`; nomor Q di bawah merujuk ke sana. Semua diuji pada respons API langsung atau dump per 2 Oktober 2026, kecuali yang ditandai (kode) atau (dokumen).

- **Subdomain `id` menyaring search, bukan pembacaan produk (Q12).** Search v2 di `id` mengembalikan 9.001 produk dan semuanya punya `en:indonesia`; di `world` ada 4.788.440. Pembacaan v3 untuk Nutella (`3017620422003`) lewat `id` tetap mengembalikan produk dengan `countries_tags: ["en:france"]`. Karena itu `is_sold_in_indonesia()` wajib di lookup dan refresh. Parameter `countries_tags_en=indonesia` dan `countries_tags=en:indonesia` sama-sama bekerja di search v2.
- **Cakupan sangat rendah (Q1, populasi dump).** Dari 8.186 produk Indonesia di dump CSV 1 Oktober 2026 (API menghitung 9.001 sehari kemudian): Nutri-Score terisi 437 (5,3%), skor lingkungan 341 (4,2%), NOVA 382 (4,7%), asal 341 (4,2%), kemasan 286 (3,5%), gambar 6.886 (84,1%), berlabel `en:halal` 1.988 (24,3%). Tujuh nutrien awal lengkap hanya pada 163 produk (2,0%). Dari 6 baris pembanding (Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama), 7.301 produk punya nol baris dan hanya 196 (194 bergambar) punya minimal 4. Sampel 100 produk dari search (Nutri-Score 67%, skor lingkungan 56%) bias ke produk populer karena search mengurutkan dari yang paling sering dipindai. Akibatnya: ketiga skor kosong untuk hampir semua produk Indonesia, sistem menghitung estimasi sendiri (bagian 7), dan Modul 4 punya bahan kerja (5.987 produk bernama dan bergambar tetapi paling banyak satu baris terisi).
- **Data halaman detail (Q13).** Pada 196 produk yang di-seed, teks bahan ada di 97,4%, berat bersih 98,5%, ukuran porsi 94,4%, dan alergen 54,6%. Pada seluruh produk Indonesia angkanya 18,4%, 49,1%, 18,7%, dan 1,9%.
- **Nilai kosong berupa string atau sel kosong, bukan `null` (Q2, Q5).** Skor yang tidak bisa dihitung berisi `"unknown"`, dan produk yang memang tidak dinilai (misalnya air mineral) berisi `"not-applicable"`. Di dump, nilai yang tidak ada berupa sel kosong. Di API, nilai gizi kosong berarti key-nya tidak ada. Kode memperlakukan semuanya sebagai tidak bisa diperingkat, tanpa pengecekan `is None`. Nilai `0` sah.
- **Nilai grade (Q2).** Nutri-Score `a` sampai `e`. Skor lingkungan `a-plus` (8 produk), `a` sampai `e`, dan `f` (11 produk). Keduanya juga bisa `unknown` dan `not-applicable`. Kode server memuat daftar yang sama (kode: `lib/ProductOpener/Display.pm:2385`).
- **Nutri-Score `"unknown"` walau data gizi lengkap (Q10).** Indomie Mi Goreng punya semua nilai gizi yang dipakai aplikasi, tetapi Nutri-Score-nya `"unknown"`. `misc_tags` mencatat sebabnya: `en:nutriscore-missing-prepared-nutrition-data` dan `en:nutriscore-not-computed`, karena kategori ini butuh gizi setelah disiapkan, bukan gizi di kemasan. Akibatnya: tabel pembanding tetap membandingkan kolom gizi walau Nutri-Score kosong; Modul 4 tidak boleh menganggap `"unknown"` sebagai tanda gizi kosong dan mendeteksi lewat `misc_tags` (kode: `lib/ProductOpener/Food.pm:1669`, `:1913`); dan asumsi 2 lebih rapuh untuk produk siap masak, yang banyak di pasar Indonesia.
- **Nama field (Q2).** Eco-Score berganti nama menjadi Green-Score pada akhir 2024, dan changelog menyatakan API v3.1 mengganti `ecoscore_*` menjadi `environmental_score_*` (dokumen). Tetapi API v2 dan v3 pada 2 Oktober 2026 masih mengembalikan `ecoscore_grade` dan tidak pernah `environmental_score_grade`, dengan atau tanpa `fields`. Dump kebalikannya: hanya `environmental_score_grade`. Kode membaca `environmental_score_grade` lebih dulu, lalu `ecoscore_grade` sebagai cadangan, di semua sumber. Untuk Nutri-Score, API mengembalikan `nutriscore_grade` dan `nutrition_grades` dengan nilai identik, dump hanya `nutriscore_grade`, dan kode membaca `nutriscore_grade` lebih dulu.
- **Skor lingkungan tidak punya nilai khusus Indonesia (Q3; kode).** `ecoscore_data.grades` berisi 63 negara dan tidak memuat `id`. Server memakai nilai `world` bila negara permintaan tidak ada (`lib/ProductOpener/EnvironmentalScore.pm:1915-1918`). Antarmuka menyebutnya "Green-Score" tanpa mengklaim skor khusus Indonesia.
- **Barcode dinormalisasi (Q4; kode).** Aturan server (`lib/ProductOpener/Products.pm:470`, `:493`, `:580`): ambil digit saja; UPC-A 12 digit dengan cek digit benar diberi satu `0` di depan; kode 14 digit berawalan `0` kehilangan nol itu; nol di depan dibuang lalu diisi sampai 13 digit; hasil 13 digit berawalan `00000` dipotong jadi EAN-8. Contoh: `089686010947` menjadi `0089686010947`, `03017620422003` menjadi `3017620422003`, `0000000000017` menjadi `00000017`. `normalize_barcode()` meniru aturan ini (tanpa pengurai GS1). Karena itu `Product.code` diisi dari `code` di respons atau dump, bukan dari ketikan pengguna, dan barcode pengguna dinormalisasi sebelum dicari di katalog lokal. Panjang kode di data Indonesia: 13 digit (7.806), 8 digit (357), 14 digit (17), dan 6 kode non-GTIN yang lebih panjang. Kode lebih dari 14 digit dilewati.
- **Format nilai gizi (Q5).** Nilai diambil dari `<nutrien>_100g`. Key per kolom Product: `energy-kcal_100g`, `proteins_100g`, `fat_100g`, `saturated-fat_100g`, `carbohydrates_100g`, `sugars_100g`, `fiber_100g`, `sodium_100g` (yang pertama dan keempat memakai tanda hubung). `sodium_100g` dalam gram: Indomie Mi Goreng 0,3976, tampil 398 mg. `energy_100g` selalu kJ, dan garam dan natrium dua key terpisah. Nilai per 100 g hasil konversi dari per sajian bisa berekor panjang (`64.7058823529412`), jadi tampilan dibulatkan. `_modifier: "~"` menandai perkiraan, dan `_prepared_100g` adalah nilai setelah disiapkan. `nova-group` di dalam `nutriments` bukan grup NOVA; grup NOVA diambil dari `nova_group` tingkat atas.
- **`countries_tags` bukan asal produk (Q12).** Indomie Mi Goreng punya `countries_tags: ["en:france", "en:indonesia"]`, yaitu negara tempat produk dijual. Asal produk diambil dari `origins_tags` (daftar tag, terisi di 3,5% produk Indonesia) dan `manufacturing_places` (teks bebas, 2,4%; gabungan keduanya 4,2%).
- **Bahasa (Q6).** `product_name_id` terisi pada 43 dari 100 produk sampel dan tidak ada di dump, jadi nama diisi berurutan dari `product_name_id`, `product_name`, `product_name_en`. Taxonomy OFF hanya punya nama Indonesia untuk 109 dari 14.717 kategori (1%) dan 7 dari 3.074 label (0%; `en:halal` tidak termasuk), jadi antarmuka butuh peta terjemahan sendiri untuk kategori dan label yang dipakai, dengan cadangan ke nama Inggris.
- **Gambar dan lisensi (Q7; dokumen).** `image_url` sama dengan `image_front_url` pada 98 dari 98 produk bergambar, ukuran 400 piksel. URL memuat nomor revisi, jadi berubah bila gambar diganti. Lisensi: ODbL untuk struktur basis data, DbCL untuk isi, CC BY-SA untuk gambar. Pengguna ulang wajib menyebut lisensi dan menyatakan OFF sebagai sumber dengan tautan ke https://openfoodfacts.org atau halaman produk. Footer menyertakan atribusi itu, dan halaman detail produk `source=off` menautkan ke halaman produknya di OFF (keputusan 26).
- **Error dan batas laju (Q8, Q9; dokumen).** Produk tidak ada: HTTP 404 dengan badan JSON (`product_not_found`). Server membalas 503 secara acak dengan badan HTML, jadi klien tidak boleh memanggil `.json()` pada 5xx dan perlu retry dengan jeda. Search v2 membalas 503 pada kira-kira separuh percobaan, pembacaan barcode v3 tidak, jadi aplikasi tidak memanggil API pada setiap permintaan halaman: data untuk tabel pembanding dan filter preferensi disimpan lokal. Batas resmi per IP: 15 permintaan per menit untuk baca produk dan 10 untuk search, dan pelampauan dijawab 503. Semua pengguna web berbagi satu IP server, jadi lookup runtime berbagi anggaran 15 per menit dan dibatasi 3 per menit per pengguna untuk sementara (keputusan 27). `page_size` search maksimum 100.

## 6. Ruang Lingkup Fungsional

Lima modul, satu per anggota kelompok. Setiap modul memiliki CRUD penuh atas entitasnya sendiri.

**Aturan Khusus tugas.** Tiap anggota mengimplementasikan modulnya dengan mencakup tujuh butir: (1) Models, baik yang dibuat sendiri, disediakan Django, maupun dipakai bersama dari modul anggota lain; (2) Views yang memproses request dan mengembalikan respons lewat template HTML maupun JSON, mencakup keempat operasi CRUD; (3) template HTML dengan kerangka sistematis (`base.html`, `header.html`, `footer.html`, dan seterusnya) dan framework CSS yang responsive; (4) Form yang menerima input dan diproses lewat Views (insert, update, delete, query data ke Models); (5) interaktivitas sisi klien (AJAX atau HTMX, sesuai Tutorial 05 dan 06); (6) filter berbasis autentikasi, yaitu sebagian informasi hanya terlihat pengguna yang sudah login; (7) filter pada data dari Public API atau mock API yang disimpan di database dan ditampilkan, misalnya berdasarkan kategori atau harga.

**Aturan filter (butir 7).** Ketentuan tugas semula meminta tiap anggota memfilter data yang diambil dari Public/mock API untuk modulnya. Ketentuan itu berubah: filter dijalankan pada data yang diambil dari **database**. Akibatnya, semua filter modul (README, butir "Filter database") membaca tabel lokal, bukan memanggil Open Food Facts. API hanya mengisi database lewat seeding, lookup barcode, dan refresh (bagian 5). Filter berbasis kolom biasa (`category`, `brand`, `nutrition_grade`, `halal_labeled`, kolom gizi) dijalankan di query; daftar tag yang disimpan di `JSONField` hanya untuk tampilan (K-3), jadi penyaringan yang bergantung pada tag dijalankan di Python atau lewat kolom turunan.

| No | Modul | Pemilik | Entitas |
|----|-------|---------|---------|
| 1 | Katalog Produk | Yasmin | `Product` (dan `ProductView`, K-5) |
| 2 | Shelf dan Tabel Pembanding | Ahmad Rizki Daffaa | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3 | Substitusi Komunitas | Rafael Arlen Wijanarko | `Substitution`, `SubstitutionVote` |
| 4 | Antrean Data | Muhammad Rayyan Basalamah | `DataCorrection`, `DataCorrectionItem` |
| 5 | Preferensi Nutrisi dan Riwayat Keputusan | Jonathan Sebastian Sindhu | `Preference`, `Decision` |

### Autentikasi (app `accounts`, Daffaa)

Dipakai semua modul untuk butir 6 Aturan Khusus (filter berbasis autentikasi), jadi bukan modul yang dinilai sendiri. Memakai `User` bawaan Django. Halamannya mengikuti frame 12 (Autentikasi) di wireframe.

| ID | Kebutuhan |
|----|-----------|
| F-0.1 | Pengunjung mendaftar dengan nama tampilan, email, password, konfirmasi password, dan persetujuan ketentuan (termasuk pernyataan bahwa PilihYuk bukan alat diagnosis medis). Email unik tanpa membedakan huruf besar dan kecil. Setelah daftar, pengguna langsung masuk |
| F-0.2 | Pengguna masuk dengan email dan password. Pesan gagal sama untuk email salah dan password salah. Dengan "Ingat saya selama 30 hari" sesi bertahan 30 hari, tanpa itu sesi berakhir saat browser ditutup |
| F-0.3 | Keluar hanya lewat permintaan POST dengan token CSRF |
| F-0.4 | Parameter `next` hanya dipatuhi bila mengarah ke situs sendiri (tanpa open redirect) |
| F-0.5 | Pendaftaran tidak pernah memberi `is_staff` atau `is_superuser`. Kurator dibuat lewat `createsuperuser` atau admin Django |
| F-0.6 | Akun dikunci 15 menit setelah 5 percobaan masuk gagal untuk email yang sama (django-axes). Dihitung per email, bukan per IP, karena semua pengguna PWS berbagi satu alamat proxy |
| F-0.7 | Halaman Profil (`/profil/`, hanya pengguna masuk) memuat data akun, ubah nama tampilan dan email, ganti password, dan kartu tautan ke Preferensi Nutrisi, Riwayat Keputusan, Shelf Saya (`/preferensi/`, `/riwayat/`, `/shelf/saya/`), serta Moderasi Data khusus `is_staff`. Kartu aktif otomatis saat URL-nya ada. Halaman ini tidak ada di wireframe |
| F-0.8 | Mengganti email wajib memasukkan password saat ini. Mengganti password mempertahankan sesi. Semua data profil diambil dari `request.user`, tanpa id di URL |
| F-0.9 | Header menampilkan Masuk dan Daftar bagi pengunjung, serta avatar inisial, nama (menaut ke Profil), dan tombol Keluar bagi pengguna masuk. Pesan sukses dan gagal tampil lewat toast |
| F-0.10 | Modul lain memakai `@login_required` (`LOGIN_URL` mengarah ke halaman Masuk, dengan `?next=`) dan `is_staff` untuk kurator. Contoh pemakaian ada di README |

Yang ditunda ada di keputusan 39.

### Modul 1: Katalog Produk

| ID | Kebutuhan |
|----|-----------|
| F-1.1 | Pengguna bisa menelusuri daftar produk dengan paginasi |
| F-1.2 | Pengguna bisa memfilter katalog (query pada tabel `Product` di database, bukan di API) berdasarkan kategori, merek, asal produk, tingkat Nutri-Score, dan label halal (`halal_labeled`, K-4). Antarmuka menulisnya "berlabel halal", bukan "halal" |
| F-1.3 | Halaman detail menampilkan seluruh skor, kandungan gizi per 100 g, kemasan, dan gambar produk |
| F-1.4 | Pengguna terdaftar bisa menambahkan produk lewat barcode atau manual. **Hanya produk Indonesia:** lewat barcode, produk dari Open Food Facts diterima hanya bila `is_sold_in_indonesia()` benar; bila tidak, penambahan ditolak dengan pesan alasan yang menawarkan jalur manual. Produk manual dianggap produk Indonesia. Produk baru langsung masuk katalog tanpa persetujuan kurator |
| F-1.5 | Pengguna terdaftar bisa menyunting dan menghapus entri manual buatannya sendiri. Kurator bisa menyunting entri manual siapa pun. Produk dari Open Food Facts dikoreksi lewat Modul 4 |
| F-1.6 | Produk yang masih dipakai shelf, usulan substitusi, atau pengajuan koreksi tidak bisa dihapus (K-1). Penghapusan produk yang tidak dipakai berupa soft delete (`is_active` menjadi salah) dan produknya hilang dari katalog |
| F-1.7 | Pencarian barcode yang belum ada di katalog mengambil data dari API runtime dan menyimpannya ke database; filter katalog tetap dijalankan pada database, tidak pada API. Barcode dinormalisasi sebelum dicari di katalog lokal. **Hanya produk Indonesia:** hasil dari Open Food Facts diperiksa dengan `is_sold_in_indonesia()` sebelum disimpan, dan refresh memeriksanya lagi (bagian 5). Kode lebih dari 14 digit ditolak |
| F-1.8 | Pencarian dan pemfilteran berjalan tanpa memuat ulang halaman |
| F-1.9 | Identitas penambah entri manual dan riwayat produk yang dilihat hanya terlihat setelah login |

### Modul 2: Shelf dan Tabel Pembanding

| ID | Kebutuhan |
|----|-----------|
| F-2.1 | Pengguna terdaftar bisa membuat shelf dengan nama, konteks toko, dan deskripsi, lalu menyunting dan menghapus shelf miliknya |
| F-2.2 | Pengguna terdaftar bisa menandai shelf sebagai privat. Shelf privat hanya terlihat oleh pemiliknya |
| F-2.3 | Pengunjung dan pengguna bisa membaca daftar shelf publik |
| F-2.4 | Pemilik shelf bisa menambah dan mengeluarkan produk tanpa memuat ulang halaman. Satu produk hanya bisa masuk satu kali ke shelf yang sama |
| F-2.5 | Shelf berisi maksimal dua belas produk, agar tidak merosot menjadi kategori |
| F-2.6 | Halaman shelf menampilkan tabel pembanding: Nutri-Score, Green-Score, NOVA, kemasan, asal, dan kandungan gizi utama (energi, protein, lemak, lemak jenuh, karbohidrat, gula, serat, natrium) |
| F-2.7 | Sistem menandai nilai terbaik pada tiap baris. Penanda hanya muncul jika minimal dua produk punya nilai yang bisa diperingkat |
| F-2.8 | Nilai `"unknown"` dan `"not-applicable"` ditampilkan apa adanya, tidak ikut diperingkat, dan ditautkan ke pengajuan koreksi di Modul 4 |
| F-2.9 | Skor lingkungan hasil estimasi ditampilkan berbeda dari nilai resmi |
| F-2.10 | Jika pengguna login dan punya preferensi aktif, urutan baris tabel mengikuti preferensi Modul 5 |
| F-2.11 | Kandidat produk saat menambahkan ke shelf bisa difilter, dengan query pada tabel `Product` di database |
| F-2.12 | Hanya pengguna terdaftar yang bisa menyimpan shelf lewat tombol "Simpan ke Shelf Saya" (ikon penanda), dan hanya shelf miliknya sendiri atau shelf publik milik orang lain. Simpanan bisa dibatalkan, tanpa memuat ulang halaman. Satu pengguna satu simpanan per shelf. Jumlah penyimpan ditampilkan di shelf publik, identitas penyimpan tidak ditampilkan |
| F-2.13 | Halaman explore shelf publik punya tombol "Shelf Saya" untuk pengguna terdaftar. Halaman itu memuat dua daftar: shelf yang dibuat pengguna itu, dan shelf publik milik orang lain yang disimpannya |
| F-2.14 | Tabel membandingkan maksimal 4 produk sekaligus, dipilih dari isi shelf (maksimal 12), sesuai wireframe desktop. Pilihan produk berupa deretan kartu kecil yang bisa dicentang |

### Modul 3: Substitusi Komunitas

| ID | Kebutuhan |
|----|-----------|
| F-3.1 | Pengguna terdaftar bisa mengusulkan bahwa produk X bisa diganti produk Y beserta alasannya. X dan Y tidak boleh produk yang sama |
| F-3.2 | Usulan punya arah: usulan X ke Y tidak otomatis berlaku untuk Y ke X |
| F-3.3 | Usulan boleh lintas shelf dan lintas kategori |
| F-3.4 | Pengusul bisa menyunting alasan dan menarik usulannya sendiri |
| F-3.5 | Pengguna terdaftar bisa memberi suara setuju atau tidak setuju. Satu pengguna punya satu suara per usulan dan bisa mengubah atau menarik suaranya |
| F-3.6 | Halaman detail produk menampilkan usulan pengganti dengan selisih suara setuju tertinggi |
| F-3.7 | Kandidat pengganti bisa difilter berdasarkan kategori dan skor, dengan query pada tabel `Product` di database |
| F-3.8 | Pengunjung melihat isi usulan tanpa identitas pengusul |
| F-3.9 | Pemberian suara berjalan tanpa memuat ulang halaman |

### Modul 4: Antrean Data

| ID | Kebutuhan |
|----|-----------|
| F-4.1 | Pengguna terdaftar bisa mengajukan koreksi untuk satu produk yang sudah ada. Satu pengajuan boleh memuat beberapa field milik produk itu. Produk baru tidak lewat modul ini, melainkan Modul 1 |
| F-4.2 | Field yang boleh dikoreksi dibatasi daftar tetap: `product_name`, `brand`, `quantity`, `category`, `origin`, `nova_group`, dan kedelapan kolom gizi. Field identitas dan kepemilikan seperti `code`, `added_by`, dan `source`, juga grade, tag, gambar, dan kolom turunan tidak bisa diajukan |
| F-4.3 | Setiap field dalam pengajuan menyimpan nilai lama saat diajukan, sehingga kurator melihat apa yang akan berubah. Satu field hanya muncul satu kali per pengajuan |
| F-4.4 | Kurator menyetujui atau menolak **per field** dengan catatan. Field yang disetujui langsung mengubah produk |
| F-4.5 | Pengaju bisa menarik pengajuannya selama belum ada field yang ditinjau |
| F-4.6 | Antrean menampilkan produk yang paling butuh dilengkapi, diurutkan berdasarkan berapa kali produk itu muncul di shelf |
| F-4.7 | Deteksi data tidak lengkap dijalankan pada data `Product` di database, memakai `misc_tags` yang tersimpan (diperiksa di Python karena disimpan di `JSONField`, K-3), misalnya `en:nutriscore-not-computed`, `en:nutriscore-missing-prepared-nutrition-data`, `en:environmental-score-not-computed`, dan `en:packagings-not-complete`. Grade `"unknown"` saja bukan bukti data gizi kosong (bagian 5). Produk yang belum punya `misc_tags` (hasil seeding dari dump) memakai kolom gizi yang kosong sebagai gantinya sampai dilengkapi (K-12) |
| F-4.8 | Pengiriman dan peninjauan pengajuan berjalan tanpa memuat ulang halaman |
| F-4.9 | Identitas pengaju dan riwayat pengajuan hanya terlihat setelah login |

### Modul 5: Preferensi Nutrisi dan Riwayat Keputusan

| ID | Kebutuhan |
|----|-----------|
| F-5.1 | Pengguna bisa menambah, menyunting, dan menghapus preferensi yang terdiri dari nutrien, arah (maksimalkan atau minimalkan), dan bobot |
| F-5.2 | Satu nutrien hanya bisa punya satu preferensi per pengguna |
| F-5.3 | Nutrien dibatasi pada yang disimpan lokal di Product (lihat bagian 7). Pilihan di antarmuka mengikuti wireframe: protein, serat, gula, natrium, lemak jenuh, dan kalori. Lemak total dan karbohidrat hanya tampil di tabel |
| F-5.4 | Preferensi menentukan urutan tabel pembanding di Modul 2 |
| F-5.5 | Pengguna bisa mencatat keputusan: produk yang dipilih, shelf asal, alasan, dan tanggal. Keputusan merujuk ke shelf, bukan ke item shelf. Pengguna bisa membaca, menyunting, dan menghapus riwayatnya |
| F-5.6 | Riwayat keputusan tetap ada walau shelf asal dihapus |
| F-5.7 | Penyuntingan preferensi menampilkan pratinjau jumlah produk yang lolos filter tanpa memuat ulang halaman |
| F-5.8 | Seluruh isi modul hanya bisa diakses pemiliknya |
| F-5.9 | Pencocokan dengan `ingredients_analysis_tags` dan `labels_tags` tidak dikerjakan di Modul 5 (K-4). Satu-satunya filter label adalah `halal_labeled` di katalog dan kandidat shelf (F-1.2, F-2.11) |

## 7. Model Data

Entitas dan field kunci. Tipe Django ditulis di tempat yang memengaruhi kebenaran. Field Product adalah usulan dan harus disetujui seluruh kelompok sebelum `makemigrations` pertama, karena Modul 2, 4, dan 5 membaca kolomnya. Keputusan K-1 sampai K-6 sudah memengaruhi daftar di bawah.

Basis data produksi PostgreSQL dan SQLite saat pengembangan lokal. PWS mensyaratkan Django 5.0 atau 5.2 dan tidak memberi tahu versi PostgreSQL-nya (keputusan 24). Daftar tag disimpan di `JSONField` hanya untuk tampilan; filter memakai kolom biasa (K-3), karena lookup `contains` pada `JSONField` tidak didukung di SQLite.

**User** (bawaan Django): `id`, `username`, `email`, `is_staff`, `date_joined`.

**Product** (usulan):

| Field | Catatan |
|-------|---------|
| `code` | `CharField(max_length=14)`, unik, boleh kosong untuk entri manual tanpa barcode. Tidak boleh angka karena barcode bisa diawali nol. Panjang 8, 13, atau 14 digit. Diisi dari `code` hasil normalisasi (bagian 5). Kode lebih dari 14 digit ditolak. Simpan `NULL`, bukan string kosong, agar constraint unik tidak bentrok |
| `product_name`, `brand`, `quantity` | Teks. `product_name` diisi dari `product_name_id`, lalu `product_name`, lalu `product_name_en`. `brand` dari `brands` yang bisa berisi beberapa merek dipisah koma (11 dari 92 di sampel) |
| `image_url` | Satu kolom, dari `image_url` Open Food Facts (ukuran 400). Sama dengan `image_front_url` |
| `category` | Satu kategori untuk tampilan dan filter katalog, diberi index. Diterjemahkan lewat peta sendiri (hanya 1% kategori punya nama Indonesia). Aturan memilih satu dari `categories_tags` (rata-rata 6,5 tag per produk) ditentukan pemilik Modul 1 |
| `categories_tags`, `packaging_tags`, `labels_tags`, `ingredients_analysis_tags`, `misc_tags` | Daftar tag di `JSONField`, hanya untuk tampilan (K-3) |
| `origin` | Teks, dari `origins_tags` (tag) atau `manufacturing_places` (teks bebas), bukan `countries_tags`. Filter negara asal hanya andal untuk produk berisi `origins_tags` |
| `nutrition_grade` | `a` sampai `e`, `"unknown"`, atau `"not-applicable"`. Diberi index. Dibaca dari `nutriscore_grade`, cadangan `nutrition_grades` |
| `environmental_grade` | Nilai resmi: `a-plus`, `a` sampai `f`, `"unknown"`, atau `"not-applicable"`. Dibaca dari `environmental_score_grade`, cadangan `ecoscore_grade` |
| `environmental_grade_estimated` | Hasil estimasi sendiri, terpisah dari nilai resmi agar tidak tertimpa refresh. Dihitung saat seeding dan refresh, disimpan di kolom agar bisa difilter dan diurutkan lewat SQL. Bahan estimasi tipis (kemasan 3,5%, asal 4,2% di populasi) |
| `nova_group` | Angka 1 sampai 4, boleh kosong. Dari `nova_group` tingkat atas, bukan `nutriments.nova-group` |
| `energy_kcal_100g`, `proteins_100g`, `fat_100g`, `saturated_fat_100g`, `carbohydrates_100g`, `sugars_100g`, `fiber_100g`, `sodium_100g` | `FloatField`, boleh kosong. Kolom terpisah, bukan satu objek JSON, agar pratinjau Modul 5 bisa dihitung dengan query. Bukan `DecimalField`, karena nilai sumber punya belasan digit desimal yang ditolak validasi form kecuali dibulatkan dulu. Tampilan dibulatkan satu desimal. Key sumber: `energy-kcal_100g` dan `saturated-fat_100g` untuk dua kolom yang namanya berbeda, enam lainnya sama dengan nama kolom. `sodium_100g` disimpan dalam gram seperti sumbernya dan ditampilkan dalam mg |
| `halal_labeled` | Boolean, benar bila `labels_tags` memuat `en:halal`. Dihitung saat seeding dan refresh (K-4). Bukan pernyataan bahwa produk halal; tanpa label berarti tidak diketahui |
| `ingredients_text` | `TextField`, boleh kosong. Teks bahan untuk halaman detail. Dari `ingredients_text_id` bila ada, lalu `ingredients_text`. Pengguna yang menambah produk manual mengisinya sendiri |
| `allergens` | `JSONField`, daftar tag alergen untuk chip di halaman detail (misalnya `en:gluten`). Dari `allergens_tags`; di dump CSV dari kolom teks `allergens`, hanya token berawalan `en:` yang dipakai karena sebagian isian berupa teks bebas |
| `serving_size` | Teks pendek, boleh kosong (misalnya `85 g`). Berat bersih memakai `quantity`. Jumlah porsi dihitung saat tampil bila keduanya berupa angka |
| `source` | `off` atau `manual` |
| `is_active` | Boolean, bawaan benar. Soft delete (K-1). Semua query katalog menyaring `is_active` |
| `added_by` | FK ke User, boleh kosong, `SET_NULL`. Produk hasil seeding tidak punya penambah |
| `created_at`, `updated_at`, `last_synced_at` | `last_synced_at` dipakai aturan refresh (K-2) |

Tautan ke halaman produk Open Food Facts dan penanda skor estimasi (`environmental_is_estimated`) dihitung saat serialisasi, bukan disimpan.

**ProductView** (K-5): `user` FK, `product` FK, `viewed_at`.

**Shelf**: `name`, `store_context`, `description`, `owner` FK, `is_private`, `created_at`, `updated_at`.

**ShelfItem**: `shelf` FK (`CASCADE`), `product` FK (`PROTECT`), `added_at`. Unik pada (`shelf`, `product`). Batas dua belas produk divalidasi di form, bukan di basis data.

**SavedShelf**: `user` FK (`CASCADE`), `shelf` FK (`CASCADE`), `created_at`. Unik pada (`user`, `shelf`). Jumlah penyimpan dihitung dengan `annotate`, bukan disimpan. Hanya pengguna terdaftar; shelf sendiri atau shelf publik orang lain (F-2.12).

**Substitution**: `from_product` FK (`PROTECT`), `to_product` FK (`PROTECT`), `reason`, `proposed_by` FK, `created_at`. `CheckConstraint` agar `from_product` berbeda dari `to_product`. Unik pada (`from_product`, `to_product`) (K-6). Tidak menyimpan penghitung suara.

**SubstitutionVote**: `substitution` FK (`CASCADE`), `user` FK, `value` (+1 atau -1), `created_at`. Unik pada (`substitution`, `user`). Jumlah suara dihitung dengan `annotate`, bukan disimpan sebagai penghitung yang bisa melenceng.

**DataCorrection**: `product` FK (`PROTECT`), `submitted_by` FK, `reviewed_by` FK (boleh kosong), `created_at`, `reviewed_at`. Satu pengajuan untuk satu produk. Tidak ada status di tingkat ini: status pengajuan diturunkan dari item (tertunda bila ada item tertunda).

**DataCorrectionItem**: `correction` FK (`CASCADE`), `field_name` (pilihan dari daftar tetap, F-4.2), `old_value`, `proposed_value`, `status` (`pending`, `approved`, `rejected`), `review_note`. Unik pada (`correction`, `field_name`). Refresh (K-2) melewati field yang punya item `approved`.

**Preference**: `user` FK, `nutrient` (salah satu dari enam kolom gizi di wireframe: protein, serat, gula, natrium, lemak jenuh, energi), `direction` (`max` atau `min`), `weight`. Unik pada (`user`, `nutrient`). Bentuk ini tetap karena filter tag dihapus (K-4).

**Decision**: `user` FK, `product` FK (`SET_NULL`), `shelf` FK (boleh kosong, `SET_NULL`), `note`, `created_at`. Merujuk ke shelf, bukan item shelf.

Aturan penanganan nilai kosong: field grade menyimpan string dari sumber apa adanya (sel kosong di dump disimpan sebagai `"unknown"`); kolom gizi dan `nova_group` menyimpan `NULL`. Keduanya sama-sama tidak diperingkat. Nilai `0` bukan kosong.

## 8. Kebutuhan Non-Fungsional

| ID | Kebutuhan |
|----|-----------|
| NF-1 | Tampilan responsif di lebar layar ponsel dan desktop, memakai framework CSS yang responsive (Bootstrap atau Tailwind, K-8). Responsif diharapkan pada pengumpulan final |
| NF-2 | Seluruh halaman memakai kerangka template bersama: `base.html`, `header.html`, `footer.html` |
| NF-3 | Views mengembalikan respons HTML dan JSON, karena endpoint JSON akan dipakai aplikasi Flutter pada Proyek Akhir Semester. Flutter hanya memanggil endpoint Django, bukan Open Food Facts langsung. Kontrak JSON: `.claude/pilihyuk-docs/off-sdk-evaluation.md` |
| NF-4 | Basis data berisi minimal 50 produk saat deployment. Target kerja 150 sampai 200 produk. Stok produk Indonesia yang datanya cukup sekitar 196 (bagian 5), jadi target kerja hampir menghabiskannya |
| NF-5 | Cakupan unit test minimal 80 persen |
| NF-6 | Aplikasi tetap berfungsi ketika Open Food Facts tidak bisa dihubungi, karena data sudah tersimpan lokal |
| NF-7 | Setiap permintaan ke API menyertakan header User-Agent yang mengidentifikasi aplikasi ini, dalam bentuk di bagian 5. Permintaan 5xx diulang dengan jeda, dan lookup dibatasi per pengguna karena batas laju resmi dipakai bersama |
| NF-8 | Deployment ke PWS berjalan otomatis lewat GitHub Actions setiap ada perubahan di `main`. Karena itu `main` hanya menerima gabungan dari `dev` yang lulus `check` dan `test` (keputusan 36) |
| NF-9 | Autentikasi (daftar, masuk, keluar, profil) dikerjakan Ahmad Rizki Daffaa di app `accounts`, langsung di branch `dev` tanpa branch sendiri karena kecil, dikerjakan sekali, dan dibutuhkan semua modul. Hanya commit yang lulus `manage.py check` dan `manage.py test` yang di-push. Anggota lain memakai hasilnya. **Status: selesai 4 Oktober** (F-0.1 sampai F-0.10, 34 tes, cakupan app `accounts` sekitar 99 persen) |
| NF-10 | Footer memuat atribusi Open Food Facts dan lisensi data (ODbL, DbCL) serta gambar (CC BY-SA), dengan tautan ke https://openfoodfacts.org. Wireframe Landing sudah memuat kalimat atribusi "Data produk berasal dari Open Food Facts"; kata lisensi dan target tautan ditambahkan di kode, misalnya pada tautan "Open Food Facts" di kolom Sumber Data dan di halaman "Kebijakan data". Footer ditulis sekali di `footer.html`, jadi tampil di semua halaman meski wireframe lain belum menggambarnya. Halaman produk dengan `source=off` memuat tautan "Lihat di Open Food Facts" ke halaman produknya (keputusan 26) |
| NF-11 | Keamanan dasar. `SECRET_KEY` dibaca dari environment (`.env` lokal dan environment variables PWS) tanpa nilai bawaan, sehingga aplikasi gagal start dengan `KeyError` bila hilang. `DEBUG` mengikuti `PRODUCTION`. Di produksi: cookie sesi dan CSRF bertanda `Secure`, HSTS 1 jam. Password disimpan dengan hash bawaan Django dan lolos empat validator bawaan. Pembatasan percobaan login: F-0.6. `SECURE_SSL_REDIRECT` dan `SECURE_PROXY_SSL_HEADER` belum dipasang sampai perilaku proxy PWS diuji |

## 9. Ukuran Keberhasilan

Untuk penilaian mata kuliah: kelima modul terintegrasi sebagai satu aplikasi, seluruh unit test lulus, cakupan test mencapai 80 persen, dan tiap anggota memenuhi ketujuh butir Aturan Khusus pada modulnya.

Untuk produknya sendiri, diukur secara manual saat demo: pengguna baru bisa membuat shelf berisi dua produk dan membaca tabel pembandingnya dalam waktu kurang dari satu menit tanpa penjelasan, dan minimal 70 persen produk hasil seeding punya cukup data untuk dibandingkan pada minimal empat dari enam baris pembanding. Target 70 persen tercapai karena seeding hanya mengambil produk yang minimal 4 dari 6 barisnya terisi; tanpa seleksi itu, angkanya 2,4 persen (bagian 5).

## 10. Asumsi

1. Open Food Facts punya cukup produk pasar Indonesia untuk mengisi katalog. **Terverifikasi untuk jumlah, tidak untuk kelengkapan**: 8.186 sampai 9.001 produk berlabel Indonesia, tetapi hanya 196 (2,4%) punya minimal 4 dari 6 baris pembanding. Cukup untuk target 50 minimum dan nyaris cukup untuk target kerja 150 sampai 200.
2. Nutri-Score tersedia lebih lengkap dibanding Green-Score, sehingga tabel pembanding tetap berguna meski sisi lingkungan banyak yang kosong. **Tidak berguna sebagai pegangan.** Nutri-Score 5,3% dan Green-Score 4,2% di populasi, selisih kecil, dan keduanya kosong untuk hampir semua produk. Sampel pertama menunjukkan kebalikannya (Indomie Mi Goreng punya Green-Score tetapi tidak punya Nutri-Score, bagian 5). Tabel pembanding bergantung pada kolom gizi per 100 g, yang terisi di 2,4 sampai 4,7% produk per nutrien, dan pada seleksi seeding.
3. Seluruh anggota kelompok sudah menyelesaikan Tutorial 05 dan 06, sehingga AJAX bukan materi baru saat implementasi dimulai.
4. Skema `tugas_kelompok` dari basis data salah satu anggota cukup untuk kebutuhan lima modul. Produksi memakai PostgreSQL, versinya tidak diberitahukan PWS (K-3, keputusan 24).
5. Target pengguna utama, yaitu mahasiswa dan pekerja muda kota besar yang belanja rutin di minimarket, masih asumsi kelompok dan belum divalidasi lewat wawancara.
6. Server PWS keluar ke internet lewat satu alamat IP, sehingga batas laju Open Food Facts (15 permintaan per menit untuk baca produk) dipakai bersama oleh semua pengguna. Dugaan, belum dicek.
7. Dump CSV (8.186 produk Indonesia) dan API (9.001) menggambarkan katalog yang sama dengan selisih waktu dan kriteria ekspor. Penyebab selisih 9% belum diketahui.

## 11. Risiko

| Risiko | Dampak | Penanganan |
|--------|--------|------------|
| Skor lingkungan dan Nutri-Score kosong untuk hampir semua produk Indonesia (95 persen) | Tabel pembanding berisi banyak nilai tidak diketahui dan fitur utama kehilangan artinya | Seeding hanya mengambil produk yang minimal 4 dari 6 barisnya terisi. Skor estimasi dihitung sendiri dan ditandai terpisah. Produk dengan data kosong ditampilkan sebagai antrean Modul 4 |
| Stok produk berdata cukup sempit (sekitar 196) | Katalog awal kecil | Produk lain masuk lewat lookup barcode dan jalur manual. Target minimum 50 aman |
| Produk non-Indonesia masuk lewat lookup atau refresh | Aturan "hanya produk Indonesia" bocor, karena subdomain `id` tidak menyaring pembacaan v3 | `is_sold_in_indonesia()` di tiga jalur, dengan tes. Produk non-Indonesia ditolak |
| Open Food Facts membalas 503 acak dengan badan HTML | Lookup gagal atau memunculkan error karena `.json()` pada HTML | Retry dengan jeda pada 5xx dan kegagalan jaringan, timeout 10 detik. Aplikasi tetap bisa dipakai dari data lokal (NF-6) |
| Semua pengguna berbagi batas 15 permintaan per menit | Lookup barcode antri atau ditolak saat ramai | Cache lokal, lookup dibatasi 3 per menit per pengguna (keputusan 27) |
| Barcode tersimpan dalam dua bentuk (12 dan 13 digit) | Produk yang sama masuk katalog dua kali dan constraint unik tidak menangkapnya | `code` selalu diisi dari respons API atau dump. Input dinormalisasi sebelum dicari |
| Field Product berubah setelah kelima modul punya migrasi | Migrasi bentrok di lima app sekaligus, pekerjaan tertunda berhari-hari | Field Product disetujui seluruh kelompok sebelum `makemigrations` pertama (bagian 7) |
| Produk dihapus dan data modul lain ikut terhapus | Shelf, usulan, dan pengajuan milik anggota lain hilang tanpa peringatan | Soft delete dan `PROTECT` dari ShelfItem, Substitution, dan DataCorrection; `SET_NULL` dari Decision (K-1). Produk yang masih dipakai tidak bisa dihapus (F-1.6) |
| Refresh dari API menimpa koreksi yang sudah disetujui | Pekerjaan kurator hilang dan antrean data tidak bermakna | Refresh melewati field yang punya `DataCorrectionItem` berstatus `approved` (K-2) |
| Pengajuan koreksi mengubah field yang tidak semestinya | Pengguna bisa mengubah kepemilikan atau barcode produk lewat kurator yang lengah | Daftar field yang boleh dikoreksi bersifat tetap (F-4.2) |
| Dump Open Food Facts berukuran gigabyte | Seeding lambat atau gagal di mesin anggota | Dump CSV (1,28 GB) dibaca secara streaming dan disaring: 148 detik unduh dan 52 detik saring (terukur). Hanya fixture hasil saringan yang masuk repositori. Dump tidak masuk repositori |
| Kerangka template dikerjakan satu orang dan anggota lain hanya memakainya | Anggota lain tidak memenuhi butir template pada penilaian individu | Pemegang design system hanya membuat kerangka bersama. Template tiap modul ditulis pemilik modulnya |
| `SECRET_KEY` tidak ada di `.env` lokal anggota atau di environment PWS | `manage.py` dan deploy berhenti dengan `KeyError: 'SECRET_KEY'` | Sengaja tanpa fallback (NF-11). Anggota menambah satu baris ke `.env` sebelum `git pull dev`. `SECRET_KEY` di PWS diisi sebelum push ke `main` (sudah dilakukan Daffaa) |
| Akun dikunci oleh pihak iseng (lockout per email, termasuk admin) | Pengguna atau kurator tidak bisa masuk 15 menit | Diterima (keputusan 40). Pantau dan reset dengan `python manage.py axes_reset`. Tambah faktor IP bila PWS terbukti meneruskan IP asli |
| `PRODUCTION=True` tidak diisi di environment PWS | `DEBUG` menyala dan database jatuh ke SQLite | Daffaa memeriksa environment PWS saat deploy. `PRODUCTION` dan `SECRET_KEY` sudah diisi |
| `Procfile` release (`collectstatic` dan `migrate`) belum teruji di PWS | Tabel `auth`, `sessions`, dan `axes` tidak terbentuk, halaman Masuk dan Daftar error | Cek log deploy pertama setelah push. Cadangan: jalankan `migrate` manual di PWS |

## 12. Linimasa

Jadwal harian dan tugas per orang ada di `timeline.md`. Tonggak utamanya:

| Tanggal | Target |
|---------|--------|
| 16 September 2026 | Checkpoint 1. Repositori, README awal, pembagian modul disepakati |
| 2 Oktober 2026 | Checkpoint 2. Kerangka template, halaman landing, Tailwind, dan deployment pertama ke PWS selesai. Enam app Django sudah didaftarkan |
| 4 Oktober | Auth (`accounts`) selesai lebih awal, 34 tes, sudah di `origin/dev` tetapi belum di `main`. Rapat: seeding, Tailwind, pemeriksaan ERD per modul |
| 10 Oktober | Akhir Fase 1. Semua model di `dev`, fixture 20 produk bisa dimuat, login berjalan, CRUD dasar dimulai |
| 18 Oktober (pagi) | Akhir Fase 2. Semua modul digabung dari `dev` ke `main`, tujuh Aturan Khusus terpenuhi, bisa didemokan di PWS |
| 21 Oktober | Responsif ponsel dan tes selesai. Fitur dibekukan malamnya (bonus dikerjakan paling cepat 20 Oktober, keputusan 37) |
| 22 Oktober | Uji penuh di PWS dengan PostgreSQL |
| 23 Oktober 2026, 23.59 WIB | Pengumpulan akhir. Seluruh modul terintegrasi dan unit test lulus |

Hari tanpa target proyek: 5, 7, 8, dan 9 Oktober (kuis dan tenggat tugas lain), 11 sampai 15 Oktober (belajar UTS dan UTS, tanpa push ke `main`), dan 19 Oktober (UTS).

## 13. Keputusan

Jawaban pada bagian ini dicatat dari Ahmad Rizki Daffaa, pemilik Modul 2, pada 2 Oktober 2026. Seluruh butir di tabel "Sudah diambil" telah disetujui kelompok dan pemilik modul masing-masing, kecuali butir 16 (seeding) yang akan dibahas lagi. Kolom Cakupan menunjukkan siapa pemilik keputusan: **Kelompok** (kelima anggota) atau **Modul N** (pemilik modul itu).

### Sudah diambil

| No | Keputusan | Cakupan |
|----|-----------|---------|
| 1 | Nama aplikasi: PilihYuk | Selesai |
| 2 | Lima modul dan pemetaannya ke anggota mengikuti README | Selesai |
| 3 | Kurator memakai `is_staff` bawaan Django, tanpa model User kustom | Selesai |
| 4 | Seeding dari dump nightly yang disaring ke Indonesia. API runtime hanya untuk pencarian barcode dan refresh satu produk | Selesai |
| 5 | `DataCorrection` hanya untuk koreksi produk yang sudah ada. Produk baru lewat Modul 1 tanpa persetujuan | Selesai |
| 6 | Autentikasi dikerjakan Daffaa langsung di `dev` (NF-9) | Selesai |
| 7 | Satu suara per pengguna per usulan substitusi, disimpan di `SubstitutionVote` | Selesai |
| 8 | **Hanya produk Indonesia**: `countries_tags` memuat `en:indonesia`, diperiksa satu fungsi `is_sold_in_indonesia()` di seeding, lookup, dan refresh (bagian 5) | Kelompok |
| 9 | **Lookup produk Open Food Facts non-Indonesia: ditolak** dengan pesan alasan yang menawarkan jalur manual. Refresh yang kehilangan label dilewati, produk tidak dihapus. Produk `source=manual` dianggap Indonesia dan tidak di-refresh | Kelompok |
| 10 | **K-1: soft delete** dengan `is_active`. Produk yang masih dipakai shelf, usulan, atau pengajuan tidak bisa dihapus (F-1.6) | Kelompok |
| 11 | **K-2:** produk `source=manual` tidak pernah di-refresh. Produk `source=off` di-refresh, kecuali field yang punya `DataCorrectionItem` berstatus `approved`. Refresh memeriksa `is_sold_in_indonesia()` lebih dulu | Kelompok |
| 12 | **K-3:** PostgreSQL di produksi, SQLite lokal. Tag di `JSONField` hanya untuk tampilan, filter lewat kolom biasa | Kelompok |
| 13 | **K-4:** filter tag dihapus dari Modul 5. Kolom `halal_labeled` di Product memberi filter "berlabel halal" di katalog dan kandidat shelf | Kelompok, Modul 1, Modul 5 |
| 14 | **K-5:** riwayat produk yang dilihat disimpan di model `ProductView` | Modul 1 |
| 15 | **K-6:** usulan substitusi unik pada (`from_product`, `to_product`); pengguna lain memberi suara | Modul 3 |
| 16 | **Seeding** dari dump CSV: produk Indonesia yang minimal 4 dari 6 baris pembanding terisi (sekitar 194), kode lebih dari 14 digit dilewati. **Akan dibahas lagi nanti**; butir ini, K-12, dan K-13 belum final | Kelompok |
| 17 | **Field Product** (bagian 7): `code` 14 karakter, `product_name` dari `_id`/default/`_en`, satu `image_url`, `origin` tetap, grade lingkungan memuat `a-plus` dan `f`, `halal_labeled`, `is_active`, key gizi bertanda hubung, kategori diterjemahkan lewat peta sendiri | Kelompok |
| 18 | **Tidak ada fork shelf.** Pengguna terdaftar menyimpan shelf miliknya sendiri atau shelf publik milik orang lain lewat "Simpan ke Shelf Saya" (`SavedShelf`). Identitas penyimpan tidak tampil. Pengunjung tidak bisa menyimpan. Nama dan ikon penanda mengikuti wireframe (keputusan 30) | Modul 2 |
| 19 | **Skor lingkungan estimasi** disimpan di kolom `environmental_grade_estimated`, dihitung saat seeding dan refresh | Kelompok |
| 20 | **`Decision`** merujuk ke `Shelf` (`SET_NULL`) dan produk yang dipilih, bukan `ShelfItem` | Modul 5 |
| 21 | **Kategori dan merek** berupa teks di Product, bukan entitas | Modul 1 |
| 22 | **`DataCorrection`:** satu pengajuan untuk satu produk dengan beberapa field (`DataCorrectionItem`), field dari daftar tetap (F-4.2), ditinjau per field | Modul 4, Modul 1 |
| 23 | **Halaman koleksi shelf:** dari halaman explore shelf publik ada tombol "Shelf Saya" ke halaman yang memuat shelf yang dibuat pengguna terdaftar dan shelf publik milik orang lain yang disimpannya (F-2.13) | Modul 2 |
| 24 | **PostgreSQL di PWS:** PWS mensyaratkan Django 5.0 atau 5.2 dan tidak memberi tahu versi PostgreSQL. Django 5.2 butuh PostgreSQL 14 atau lebih baru (dibaca dari kodenya), jadi `requirements.txt` diubah ke `django~=5.2.0` (keputusan 42) | Selesai |
| 25 | **Responsif** pada pengumpulan final (NF-1) | Kelompok |
| 26 | **Atribusi Open Food Facts:** kalimat atribusi dan lisensi di footer, ditambah tautan "Lihat di Open Food Facts" pada produk yang datanya berasal dari Open Food Facts (`source=off`) (NF-10, F-1.3) | Kelompok |
| 27 | **Pembatasan lookup runtime:** 3 lookup barcode ke Open Food Facts per menit per pengguna, untuk sementara. Hasil disimpan di database, jadi barcode yang sudah ada tidak dihitung (NF-7) | Kelompok |
| 28 | **Framework CSS: Tailwind CSS (K-8).** Dipilih setelah wireframe dibaca (14 bagian, semuanya desktop 1440 piksel). Desain memakai token sendiri (hijau merek, latar krem, kartu membulat, chip pil, lencana skor) yang langsung dipetakan ke utility Tailwind, sedangkan Bootstrap perlu menimpa hampir semua komponen. Bootstrap tetap sah bila tim tidak ingin langkah build. Tailwind dimuat lewat script CDN (`@tailwindcss/browser`), tanpa Node, CLI, atau build; butuh internet saat halaman dibuka | Kelompok |
| 29 | **Nutrien (K-16):** `salt_100g` diganti `sodium_100g` (gram, tampil mg) dan `carbohydrates_100g` ditambah. Pilihan preferensi: protein, serat, gula, natrium, lemak jenuh, energi | Kelompok, Modul 1, Modul 4, Modul 5 |
| 30 | **Nama fitur simpan shelf (K-17):** "Simpan ke Shelf Saya" dengan ikon penanda, mengikuti wireframe. Entitas `SavedShelf` | Modul 2 |
| 31 | **Halaman detail produk (K-18):** Open Food Facts menyediakan teks bahan, alergen, berat bersih, dan ukuran porsi, jadi tidak perlu input manual untuk produk dari Open Food Facts. Product bertambah `ingredients_text`, `allergens`, `serving_size`. Produk manual mengisinya lewat form (boleh kosong). "Dapat didaur ulang" tidak ada di Open Food Facts dan dihapus dari wireframe; jumlah porsi dihitung dari berat bersih dan ukuran porsi | Kelompok, Modul 1 |
| 32 | **Wireframe lanjutan (K-19, K-9):** footer sudah ada di frame Landing (02) dengan baris "© 2026 PilihYuk · Data produk berasal dari Open Food Facts.", kolom "Sumber Data" yang memuat "Open Food Facts", tautan "Kebijakan data", dan baris "PilihYuk bukan alat diagnosis atau nasihat medis.". Yang belum ada: kata lisensi (ODbL, CC BY-SA), target tautan ke https://openfoodfacts.org, dan footer di layar lain. Tim akan menambahkan frame ponsel dan tautan "Lihat di Open Food Facts" di halaman detail produk ke wireframe. Usulan untuk ponsel disimpan: tabel pembanding 2 produk per layar dengan geser horizontal, metrik tetap di kolom kiri. Detailnya ditinjau saat frame ponsel selesai | Kelompok |
| 33 | **Struktur app dan auth.** Enam app Django: `accounts` (auth), `product_catalog` (Modul 1), `shelves` (Modul 2), `substitutions` (Modul 3), `data_correction` (Modul 4), `preferences` (Modul 5, memuat `Preference` dan `Decision`). Kerangkanya sudah dibuat dan didaftarkan di `INSTALLED_APPS`. Template tiap app di `templates/<app>/`, JavaScript di `static/js/<app>.js`. Daffaa mengerjakan auth, menggantikan keputusan sebelumnya bahwa auth dikerjakan bersama | Semua modul |
| 34 | **Data halaman landing.** `pilihyuk/views.py` memuat data contoh dari wireframe. Dua fungsi, `featured_shelf()` dan `featured_shelves()`, nantinya diganti dengan query `Shelf` dan `Product`. Kunci data yang dibaca template tercatat di komentar atas `SAMPLE_PRODUCTS`. Nilai kosong tampil sebagai "Tidak diketahui" dan tidak ikut diperingkat. Warna Nutri-Score tersedia untuk A sampai E | Modul 1, 2 |
| 35 | **Penamaan.** App Modul 1 bernama `product_catalog` (bukan `catalog`), dan entitas serta app Modul 4 bernama `DataCorrection` dan `DataCorrectionItem` di app `data_correction` (bukan `DataFlag` dan `dataflags`), karena isinya pengajuan koreksi per field, bukan sekadar tanda. Kolom penghubungnya `correction`. Berlaku di seluruh dokumen ini dan di ERD (`.drawio` dan Mermaid). Salinan di Google Drive (tautan README) sudah diperbarui | Modul 1, 4 |
| 36 | **Alur branch.** Tiap modul atau app punya branch sendiri, kecuali auth (`accounts`) yang dikerjakan langsung di `dev` (NF-9). Branch digabung ke `dev` untuk diuji bersama (`manage.py check` dan `manage.py test`), lalu `dev` di-push ke `main`, yang sekaligus men-deploy ke PWS. Branch `dev` dan `shelves` sudah ada di GitHub | Semua modul |
| 37 | **Wajib dulu, bonus belakangan.** Karena kuis, tugas lain, dan UTS menyisakan sekitar tujuh hari kerja, tiap modul menyelesaikan tujuh Aturan Khusus lebih dulu. Bonus, dikerjakan paling cepat 20 Oktober: urutan tabel pembanding mengikuti preferensi (diutamakan), antrean kontribusi diurutkan menurut frekuensi di shelf, skor lingkungan estimasi, refresh produk dari Open Food Facts, dan frame ponsel di Figma. Usulan, disepakati di rapat 4 Oktober | Semua modul |
| 38 | **Login dengan email tanpa model User kustom.** `username` berisi email huruf kecil, nama tampilan di `first_name`, `ModelBackend` bawaan. Email unik dicek tanpa membedakan huruf besar dan kecil (kolom `email` Django tidak unik di database). Akun admin dari `createsuperuser` masuk dengan username-nya di kolom "Email" | Kelompok |
| 39 | **Ditunda:** verifikasi email, reset password, masuk dengan Google (tombol nonaktif di halaman Masuk), pembatasan pendaftaran, halaman Ketentuan Layanan. Email tidak diverifikasi, jadi pesan "email sudah terdaftar" di form daftar diterima sebagai kompromi | Kelompok |
| 40 | **Pembatasan percobaan login: django-axes**, 5 gagal per email, kunci 15 menit, direset saat berhasil. Per email, bukan per IP, karena semua pengguna PWS berbagi satu IP proxy. Akibat yang diterima: akun orang lain (termasuk admin) bisa dikunci sementara oleh pihak iseng. Pemulihan: `python manage.py axes_reset` | Kelompok |
| 41 | **Halaman Profil** (`/profil/`) berupa hub dengan data akun, ganti password, dan kartu tautan ke modul lain (F-0.7). Wireframe tidak memilikinya; frame Preferensi hanya memakai breadcrumb "Profil" dan avatar inisial. Ganti email wajib password saat ini | Daffaa, Modul 2, Modul 5 |
| 42 | **Konfigurasi.** `SECRET_KEY` dari environment tanpa fallback; kunci lama sudah ter-commit, jadi diganti dan dibedakan antara lokal dan produksi. `DEBUG = not PRODUCTION`. `django~=5.2.0` dan `django-axes~=8.3`. `LANGUAGE_CODE = 'id'`, sehingga pesan Django berbahasa Indonesia dan desimal berkoma ("7,5 g"). `Procfile` menjalankan `collectstatic` dan `migrate` saat rilis. Label form mengikuti wireframe ("Password"), sedangkan pesan bawaan Django menulis "kata sandi" | Kelompok |

### Belum diambil

Tiap butir punya usulan bawaan. Kelompok cukup menyetujui atau memilih alternatif. K-8, K-9, K-10, K-11, K-14, K-15, dan K-16 sampai K-19 sudah selesai (keputusan 18, 23, 24, dan 26 sampai 32) dan nomornya tidak dipakai lagi.

| No | Keputusan | Usulan bawaan | Alternatif dan akibatnya |
|----|-----------|---------------|--------------------------|
| K-7 | Cache Redis. Kelompok belum mempelajari Redis, tetapi caching dinilai berguna | Tidak dipakai di versi ini. Ide caching disimpan di bawah tabel ini | Dipakai untuk hasil API runtime. Butuh konfirmasi bahwa PWS menyediakan Redis |
| K-12 | Melengkapi `misc_tags` dan `product_name_id` untuk produk hasil seeding (dump CSV tidak memuatnya). Dibahas bersama seeding nanti | Sekali, lewat v3 per barcode, 4,5 detik per request, sekitar 15 menit untuk 194 produk | Menunggu refresh pertama. Tanpa langkah ini, F-4.7 memakai kolom gizi kosong sebagai pengganti |
| K-13 | Seberapa sering seeding dijalankan ulang. Dibahas bersama seeding nanti | Sekali sebelum pengumpulan | Berkala. Fixture lama tidak menangkap produk yang baru dilengkapi di Open Food Facts |

### Ide yang disimpan: caching

Redis belum dipelajari kelompok (K-7), tetapi caching dinilai berguna. Ide untuk dipertimbangkan nanti, belum menjadi kebutuhan:
- Cache hasil lookup barcode dari Open Food Facts dengan masa berlaku, supaya barcode yang sama tidak dipanggil ulang dan batas 15 permintaan per menit (bagian 5) lebih terjaga.
- Cache tabel pembanding shelf publik, dan jumlah penyimpan per shelf.
- Pakai framework cache bawaan Django, dimulai dari backend yang tidak butuh layanan tambahan (memori lokal atau tabel di database), lalu pindah ke Redis bila sudah dipelajari dan PWS menyediakannya. Ini usulan, belum dicek ke PWS.

## 14. Verifikasi yang Belum Dikerjakan

Sudah terverifikasi dan dicatat di `off-api-findings.md` (perilaku Open Food Facts) dan `off-sdk-evaluation.md` (SDK Python dijalankan, Dart hanya dibaca): nilai kosong, grade, nama field, normalisasi barcode, cakupan, filter Indonesia, error, dan rate limit. Dua hal lain:
- Django 5.2.17 membutuhkan PostgreSQL 14 atau lebih baru (baca kode). `requirements.txt` kini `django~=5.2.0` (keputusan 42).
- Auth, diuji lokal dengan SQLite pada 4 Oktober: 37 tes lulus (34 di `accounts`, 3 di `pilihyuk`), bandit dan pip-audit tanpa temuan, dan `check --deploy` produksi hanya menyisakan 3 peringatan yang disengaja (HSTS subdomain, preload, SSL redirect). Alur daftar sampai keluar dan penguncian akun dicoba di browser, dan lebar 390 piksel tidak overflow. `django-axes` 8.3.1 mendukung Django 5.2 (dari metadata paket).

Belum dikerjakan:
1. Kode 429: tidak ada di dokumen dan tidak dipicu. Penanganannya disamakan dengan 503.
2. Search-a-licious dan parameter `lc`/`tags_lc` tidak diuji.
3. Penyebab selisih 8.186 (dump) dan 9.001 (API) produk Indonesia (asumsi 7).
4. Apakah `grades.world` dan `grades.fr` pernah berbeda pada produk lain. Satu produk diuji.
5. Perilaku `environmental_score_grade` pada produk yang disimpan ulang setelah skema 1000. Nol dari 101 produk teruji memakainya.
6. SDK Dart tidak dijalankan karena tidak ada toolchain Flutter dan PAS belum dimulai.
7. Dump JSONL dan Parquet tidak dijalankan end-to-end; hanya CSV.
8. Apakah server PWS keluar lewat satu IP (asumsi 6).
9. Pengisian `product_name_id`, `misc_tags`, dan `states_tags` dari API untuk ratusan produk sekaligus (K-12).
10. `Procfile` belum dicoba di PWS. Satu-satunya sumber adalah ringkasan dokumentasi PWS (tidak dibaca utuh): `Procfile` dipakai dan baris `release` menjalankan migrasi.
11. Apakah proxy PWS meneruskan `X-Forwarded-Proto` dan IP asli pengguna. Jawabannya menentukan apakah `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, dan lockout per IP aman dipasang.
12. Auth di PostgreSQL 14 milik PWS (baru dicoba di SQLite).
13. Tampilan Masuk, Daftar, dan Profil di ponsel sungguhan dan di PWS. Frame ponsel di Figma belum ada.
