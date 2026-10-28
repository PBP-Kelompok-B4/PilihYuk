# Product Requirements Document

**Produk:** PilihYuk, pembanding gizi dan dampak lingkungan makanan dan minuman per shelf
**Konteks:** Proyek Tengah Semester PBP (CSGE602022), Fasilkom UI, Gasal 2026/2027, Kelompok 4 Kelas B, sub-tema Sustainable Food & Diet
**Versi:** 0.7, 28 Oktober 2026. Tenggat 30 Oktober 2026, 23.59 WIB.
**Status:** draf kerja. README adalah sumber kebenaran untuk pembagian modul. Bukti perilaku API ada di `off-api-findings.md`.

## Riwayat versi

- **v0.7 (28 Okt).** Model data disamakan dengan kode di `dev`: Modul 3 memakai `Recommendation` dan `RecommendationVote` (app `recommendations`), `Decision` menyimpan jumlah produk yang dibandingkan, dan `OffLookupQuota` dicatat.
- **v0.6 (24 Okt).** Login menerima email atau username, password wajib berisi huruf dan angka, centang persetujuan dihapus, masuk dengan Google dibatalkan, reset password direncanakan (`reset-password-plan.md`). Dokumen diringkas dan dipindah dari `pilihyuk-docs/` ke `.claude/`.
- **v0.5 (23 Okt).** Tenggat diundur ke 30 Oktober. Modul 3 bernama Rekomendasi Komunitas (app dan model tetap `substitutions`). Seeding Modul 1 berisi 406 produk.
- **v0.4 (4 Okt).** Autentikasi selesai.
- **v0.3.** Hanya produk Indonesia, seeding dari dump CSV, wireframe Figma dibaca, filter berjalan di database.
- **v0.2.** Nama PilihYuk, unit pembanding berupa shelf, lima modul mengikuti README.

## 1. Masalah

Dua produk di rak yang sama bisa berbeda jauh gizi dan dampak lingkungannya, tapi kemasannya tidak menunjukkan itu. Label seperti "alami" dan "rendah gula" tidak terstandar. Data terstandar (Nutri-Score, NOVA, Green-Score) ada di Open Food Facts, tapi berbahasa Inggris, disusun per kategori, dan tidak dibuka orang saat berbelanja. Padahal pilihan di depan rak sering lintas kategori, misalnya susu UHT, krimer, dan oat milk untuk kopi.

## 2. Tujuan produk

1. Pengguna mengumpulkan produk yang saling menggantikan ke satu shelf dan melihat perbedaannya dalam satu tabel.
2. Shelf bisa dibuka lagi dan dipakai pengguna lain.
3. Pengguna menyatakan preferensi nutrisi dua arah (misalnya maksimalkan protein), dan urutan tabel mengikutinya.
4. Pengguna mengusulkan produk pengganti lintas shelf, dan komunitas menilainya.
5. Pengguna memperbaiki data produk yang keliru atau kosong. 89% produk Indonesia di Open Food Facts tidak punya satu pun baris pembanding yang terisi.

## 3. Bukan tujuan

Pemindaian barcode lewat kamera (untuk Flutter di PAS), perbandingan harga, rekomendasi berbasis machine learning, pelacakan asupan harian, saran gizi atau kesehatan, mengirim koreksi ke Open Food Facts, produk yang tidak dijual di Indonesia, dan fork shelf (diganti "Simpan ke Shelf Saya").

## 4. Pengguna

| Peran | Yang bisa dilakukan |
|-------|---------------------|
| Pengunjung | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, membaca usulan rekomendasi tanpa identitas pengusul |
| Pengguna terdaftar | Semua di atas, ditambah mengelola shelf, menyimpan shelf, mengusulkan rekomendasi dan memberi suara, mengajukan koreksi, mengatur preferensi, mencatat keputusan |
| Kurator | Pengguna dengan `is_staff`. Meninjau koreksi (Modul 4) dan menyunting produk manual milik siapa pun (Modul 1). Produk dari Open Food Facts dikoreksi lewat `DataCorrection`, tidak disunting langsung |

## 5. Sumber data

Open Food Facts (OFF), gratis tanpa API key untuk baca. Baca barcode lewat API v3 di `id.openfoodfacts.org`, pencarian terstruktur lewat `/api/v2/search`, seeding dari dump CSV (`en.openfoodfacts.org.products.csv.gz`, 1,28 GB). Setiap permintaan memakai User-Agent `PilihYuk/0.1 (PBP Fasilkom UI; https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/; https://github.com/pbp-Kelompok-B4/PilihYuk/)`.

**Hanya produk Indonesia.** Produk masuk hanya bila `countries_tags` memuat `en:indonesia` (negara tempat dijual, bukan negara asal). Satu fungsi `is_sold_in_indonesia()` dipakai di seeding (baris dilewati), lookup barcode (ditolak dengan pesan dan tawaran input manual), dan refresh (dilewati, data lokal tidak ditimpa). Produk `source=manual` dianggap Indonesia dan tidak pernah di-refresh.

**Fakta yang memengaruhi rancangan** (rincian dan bukti di `off-api-findings.md`):

- Subdomain `id` menyaring search tapi tidak menyaring baca barcode v3, jadi pemeriksaan Indonesia wajib di lookup dan refresh.
- Cakupan sangat rendah. Dari 8.186 produk Indonesia di dump: Nutri-Score 5,3%, skor lingkungan 4,2%, NOVA 4,7%, asal 4,2%, kemasan 3,5%, gambar 84,1%, berlabel halal 24,3%. Hanya 196 produk punya minimal 4 dari 6 baris pembanding.
- Nilai kosong berupa `"unknown"` atau `"not-applicable"` (grade) atau key yang tidak ada (gizi), bukan `null`. Semuanya tidak diperingkat. Nilai `0` sah.
- Grade Nutri-Score `a` sampai `e`. Skor lingkungan juga bisa `a-plus` dan `f`.
- Nutri-Score bisa `"unknown"` walau gizi lengkap (produk yang butuh gizi setelah dimasak). Deteksi data kosong memakai `misc_tags`, bukan grade.
- Nama field skor lingkungan berbeda: API mengembalikan `ecoscore_grade`, dump memakai `environmental_score_grade`. Kode membaca nama baru dulu, lalu nama lama.
- Skor lingkungan tidak punya nilai khusus Indonesia, jadi antarmuka menyebutnya Green-Score tanpa klaim lokal.
- Barcode dinormalisasi seperti server OFF (`normalize_barcode()`). `Product.code` diisi dari respons, bukan dari ketikan pengguna. Kode lebih dari 14 digit ditolak.
- Kunci gizi `energy-kcal_100g` dan `saturated-fat_100g` memakai tanda hubung. `sodium_100g` dalam gram, ditampilkan dalam mg.
- Nama produk: `product_name_id`, lalu `product_name`, lalu `product_name_en`. Taxonomy OFF hampir tidak punya nama Indonesia, jadi kategori butuh peta terjemahan sendiri.
- Lisensi: ODbL (struktur), DbCL (isi), CC BY-SA (gambar). Footer memuat atribusi, dan detail produk `source=off` menaut ke halamannya di OFF.
- Server membalas 503 acak dengan badan HTML. Klien tidak boleh memanggil `.json()` pada 5xx dan perlu retry. Batas resmi 15 baca produk per menit per IP. Semua pengguna PWS berbagi satu IP, jadi lookup dibatasi 3 per menit per pengguna.

## 6. Ruang lingkup fungsional

**Aturan Khusus.** Tiap anggota mencakup tujuh butir di modulnya: (1) models, (2) views HTML dan JSON untuk keempat operasi CRUD, (3) template dengan kerangka bersama dan CSS responsif, (4) form, (5) AJAX atau HTMX, (6) filter berbasis autentikasi, (7) filter pada data di **database**, bukan dengan memanggil API. API hanya mengisi database lewat seeding, lookup, dan refresh. Filter memakai kolom biasa. Tag di `JSONField` hanya untuk tampilan.

| No | Modul | Pemilik | Entitas |
|----|-------|---------|---------|
| 1 | Katalog Produk | Yasmin | `Product`, `ProductView` |
| 2 | Shelf dan Tabel Pembanding | Ahmad Rizki Daffaa | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3 | Rekomendasi Komunitas | Rafael Arlen Wijanarko | `Recommendation`, `RecommendationVote` |
| 4 | Antrean Data | Muhammad Rayyan Basalamah | `DataCorrection`, `DataCorrectionItem` |
| 5 | Preferensi Nutrisi dan Riwayat Keputusan | Jonathan Sebastian Sindhu | `Preference`, `Decision` |

### Autentikasi (app `accounts`, Daffaa)

Dipakai semua modul untuk butir 6, jadi tidak dinilai sendiri. Memakai `User` bawaan Django.

| ID | Kebutuhan |
|----|-----------|
| F-0.1 | Pendaftaran dengan nama tampilan, email, password, dan konfirmasi password. Email unik tanpa membedakan huruf besar dan kecil, dan disimpan huruf kecil sebagai username. Setelah daftar, pengguna langsung masuk |
| F-0.2 | Masuk dengan email atau username dan password. Bila isian berupa email yang bukan username, akun dicari lewat kolom email. Pesan gagal sama untuk semua kasus. "Ingat saya" membuat sesi bertahan 30 hari, tanpa itu sesi berakhir saat browser ditutup |
| F-0.3 | Keluar hanya lewat POST dengan CSRF |
| F-0.4 | `next` hanya dipatuhi bila mengarah ke situs sendiri |
| F-0.5 | Pendaftaran tidak pernah memberi `is_staff` atau `is_superuser`. Kurator dibuat lewat `createsuperuser` atau admin |
| F-0.6 | Akun dikunci 15 menit setelah 5 kali gagal (django-axes), dihitung per akun karena semua pengguna PWS berbagi IP proxy |
| F-0.7 | Halaman Profil (`/profil/`) memuat data akun, ubah nama dan email, ganti password, dan kartu ke Preferensi, Riwayat, Shelf Saya, serta Moderasi untuk `is_staff`. Kartu aktif sendiri saat URL-nya ada |
| F-0.8 | Mengganti email wajib memasukkan password saat ini. Mengganti password mempertahankan sesi |
| F-0.9 | Header menampilkan Masuk dan Daftar bagi pengunjung, serta avatar, nama, dan Keluar bagi pengguna masuk. Pesan tampil lewat toast |
| F-0.10 | Modul lain memakai `@login_required` (dengan `?next=`) dan `is_staff` |
| F-0.11 | Lupa password: tautan sekali pakai lewat email, berlaku 1 jam. Halaman konfirmasi sama untuk email terdaftar dan tidak, supaya akun tidak bisa ditebak (`reset-password-plan.md`) |

### Modul 1: Katalog Produk

| ID | Kebutuhan |
|----|-----------|
| F-1.1 | Daftar produk berpaginasi |
| F-1.2 | Filter di database: kategori, merek, asal, Nutri-Score, dan "berlabel halal" (`halal_labeled`) |
| F-1.3 | Detail menampilkan skor, gizi per 100 g, kemasan, dan gambar |
| F-1.4 | Pengguna terdaftar menambah produk lewat barcode (hanya produk Indonesia, selain itu ditolak dengan tawaran input manual) atau manual. Produk baru langsung masuk tanpa persetujuan kurator |
| F-1.5 | Pengguna menyunting dan menghapus produk manual buatannya. Kurator bisa menyunting produk manual siapa pun |
| F-1.6 | Produk yang masih dipakai shelf, usulan, atau pengajuan koreksi tidak bisa dihapus. Hapus berupa soft delete (`is_active`) |
| F-1.7 | Barcode yang belum ada diambil dari API lalu disimpan. Barcode dinormalisasi dulu, hasilnya diperiksa `is_sold_in_indonesia()`, dan kode lebih dari 14 digit ditolak |
| F-1.8 | Pencarian dan filter tanpa memuat ulang halaman |
| F-1.9 | Penambah produk manual dan riwayat produk yang dilihat hanya terlihat setelah login |

### Modul 2: Shelf dan Tabel Pembanding

| ID | Kebutuhan |
|----|-----------|
| F-2.1 | Pengguna terdaftar membuat, menyunting, dan menghapus shelf (nama, konteks toko, deskripsi) |
| F-2.2 | Shelf bisa privat dan hanya terlihat pemiliknya |
| F-2.3 | Siapa pun bisa membaca daftar shelf publik |
| F-2.4 | Pemilik menambah dan mengeluarkan produk tanpa memuat ulang halaman. Satu produk satu kali per shelf |
| F-2.5 | Maksimal 12 produk per shelf |
| F-2.6 | Tabel pembanding: Nutri-Score, Green-Score, NOVA, kemasan, asal, dan gizi utama (energi, protein, lemak, lemak jenuh, karbohidrat, gula, serat, natrium) |
| F-2.7 | Nilai terbaik tiap baris ditandai, hanya bila minimal dua produk punya nilai yang bisa diperingkat |
| F-2.8 | `"unknown"` dan `"not-applicable"` tampil apa adanya, tidak diperingkat, dan menaut ke pengajuan koreksi Modul 4 |
| F-2.9 | Skor lingkungan estimasi tampil berbeda dari nilai resmi |
| F-2.10 | Bila pengguna login dan punya preferensi, urutan baris mengikuti Modul 5 |
| F-2.11 | Kandidat produk bisa difilter lewat query di database |
| F-2.12 | Pengguna terdaftar menyimpan shelf sendiri atau shelf publik orang lain ("Simpan ke Shelf Saya") dan bisa membatalkannya tanpa memuat ulang halaman. Satu simpanan per pengguna per shelf. Jumlah penyimpan tampil, identitasnya tidak |
| F-2.13 | Halaman Shelf Saya memuat shelf buatan sendiri dan shelf publik orang lain yang disimpan |
| F-2.14 | Tabel membandingkan maksimal 4 produk, dipilih dari isi shelf lewat kartu kecil yang bisa dicentang |

### Modul 3: Rekomendasi Komunitas

| ID | Kebutuhan |
|----|-----------|
| F-3.1 | Pengguna terdaftar mengusulkan produk X bisa diganti Y beserta alasan. X dan Y harus berbeda |
| F-3.2 | Usulan punya arah: X ke Y tidak berarti Y ke X |
| F-3.3 | Usulan boleh lintas shelf dan kategori |
| F-3.4 | Pengusul bisa menyunting alasan dan menarik usulannya |
| F-3.5 | Satu suara (setuju atau tidak) per pengguna per usulan, bisa diubah atau ditarik |
| F-3.6 | Detail produk menampilkan usulan dengan selisih suara tertinggi |
| F-3.7 | Kandidat pengganti difilter menurut kategori dan skor di database |
| F-3.8 | Pengunjung melihat usulan tanpa identitas pengusul |
| F-3.9 | Pemberian suara tanpa memuat ulang halaman |

### Modul 4: Antrean Data

| ID | Kebutuhan |
|----|-----------|
| F-4.1 | Pengguna terdaftar mengajukan koreksi untuk satu produk, boleh beberapa field sekaligus |
| F-4.2 | Field yang boleh dikoreksi: `product_name`, `brand`, `quantity`, `category`, `origin`, `nova_group`, dan delapan kolom gizi. Identitas, kepemilikan, grade, tag, gambar, dan kolom turunan tidak boleh |
| F-4.3 | Tiap field menyimpan nilai lama saat diajukan. Satu field satu kali per pengajuan |
| F-4.4 | Kurator menyetujui atau menolak per field dengan catatan. Yang disetujui langsung mengubah produk |
| F-4.5 | Pengaju bisa menarik pengajuan selama belum ada field yang ditinjau |
| F-4.6 | Antrean menampilkan produk yang paling butuh dilengkapi, diurutkan menurut berapa kali muncul di shelf |
| F-4.7 | Deteksi data kosong memakai `misc_tags` (dicek di Python) atau kolom gizi kosong bila `misc_tags` belum ada. Grade `"unknown"` saja bukan bukti |
| F-4.8 | Kirim dan tinjau tanpa memuat ulang halaman |
| F-4.9 | Identitas pengaju dan riwayat pengajuan hanya terlihat setelah login |

### Modul 5: Preferensi Nutrisi dan Riwayat Keputusan

| ID | Kebutuhan |
|----|-----------|
| F-5.1 | Tambah, sunting, dan hapus preferensi: nutrien, arah (maks atau min), dan bobot |
| F-5.2 | Satu preferensi per nutrien per pengguna |
| F-5.3 | Nutrien: protein, serat, gula, natrium, lemak jenuh, dan energi |
| F-5.4 | Preferensi menentukan urutan tabel pembanding Modul 2 |
| F-5.5 | Catat keputusan: produk terpilih, shelf asal, alasan, tanggal. Bisa dibaca, disunting, dan dihapus |
| F-5.6 | Riwayat tetap ada walau shelf asal dihapus |
| F-5.7 | Pratinjau jumlah produk yang lolos tanpa memuat ulang halaman |
| F-5.8 | Seluruh isi modul hanya untuk pemiliknya |
| F-5.9 | Tidak ada pencocokan tag. Satu-satunya filter label adalah `halal_labeled` |

## 7. Model data

PostgreSQL di produksi, SQLite lokal. Tag disimpan di `JSONField` hanya untuk tampilan, karena lookup `contains` tidak didukung SQLite.

**User** (bawaan): `username` (email huruf kecil untuk akun dari halaman Daftar), `email`, `first_name` (nama tampilan), `is_staff`.

**Product**

| Field | Catatan |
|-------|---------|
| `code` | `CharField(max_length=14)`, unik, `NULL` untuk produk manual tanpa barcode. Hasil normalisasi, disimpan sebagai teks |
| `product_name`, `brand`, `quantity`, `image_url` | Teks. Satu `image_url` ukuran 400 |
| `category` | Satu kategori untuk tampilan dan filter, diberi index |
| `origin` | Dari `origins_tags` atau `manufacturing_places`, bukan `countries_tags` |
| `nutrition_grade` | `a` sampai `e`, `"unknown"`, `"not-applicable"`. Diberi index |
| `environmental_grade` | Nilai resmi `a-plus`, `a` sampai `f`, `"unknown"`, `"not-applicable"` |
| `environmental_grade_estimated` | Estimasi sendiri, terpisah supaya tidak tertimpa refresh |
| `nova_group` | 1 sampai 4, boleh kosong |
| Delapan kolom gizi `*_100g` | `FloatField`, boleh kosong. `sodium_100g` dalam gram |
| `halal_labeled` | Benar bila `labels_tags` memuat `en:halal`. Bukan pernyataan halal |
| `ingredients_text`, `allergens`, `serving_size` | Untuk halaman detail |
| `categories_tags`, `packaging_tags`, `labels_tags`, `ingredients_analysis_tags`, `misc_tags` | `JSONField`, untuk tampilan saja |
| `source` | `off` atau `manual` |
| `is_active` | Soft delete. Semua query katalog menyaringnya |
| `added_by` | FK User, `SET_NULL` |
| `created_at`, `updated_at`, `last_synced_at` | |

Tautan ke OFF dan penanda estimasi dihitung saat serialisasi.

- **ProductView:** `user`, `product`, `viewed_at`.
- **OffLookupQuota:** `user` (kunci utama, `CASCADE`), `timestamps` (waktu lookup barcode terakhir), `version` (compare-and-swap untuk batas 3 lookup per menit).
- **Shelf:** `name`, `store_context`, `description`, `owner` (`CASCADE`), `is_private`, `created_at`, `updated_at`.
- **ShelfItem:** `shelf` (`CASCADE`), `product` (`PROTECT`), `added_at`. Unik (`shelf`, `product`). Batas 12 dicek di form.
- **SavedShelf:** `user` (`CASCADE`), `shelf` (`CASCADE`), `created_at`. Unik (`user`, `shelf`). Jumlah penyimpan dihitung dengan `annotate`.
- **Recommendation:** `source_product` dan `replacement_product` (`PROTECT`), `reason`, `author`, `created_at`, `updated_at`. Kedua produk berbeda, unik (`source_product`, `replacement_product`).
- **RecommendationVote:** `recommendation` (`CASCADE`), `user`, `value` (+1 atau -1), `created_at`, `updated_at`. Unik (`recommendation`, `user`). Jumlah suara dihitung dengan `annotate`.
- **DataCorrection:** `product` (`PROTECT`), `submitted_by`, `reviewed_by` (boleh kosong), `created_at`, `reviewed_at`. Status diturunkan dari item.
- **DataCorrectionItem:** `correction` (`CASCADE`), `field_name`, `old_value`, `proposed_value`, `status` (`pending`, `approved`, `rejected`), `review_note`. Unik (`correction`, `field_name`). Refresh melewati field berstatus `approved`.
- **Preference:** `user`, `nutrient`, `direction` (`max` atau `min`), `weight`. Unik (`user`, `nutrient`).
- **Decision:** `user`, `product` (`SET_NULL`), `shelf` (boleh kosong, `SET_NULL`), `note`, `compared_product_count` (boleh kosong, jumlah produk yang dibandingkan saat dipilih dari tabel), `created_at`.

## 8. Kebutuhan non-fungsional

| ID | Kebutuhan |
|----|-----------|
| NF-1 | Responsif di ponsel dan desktop (Tailwind) |
| NF-2 | Kerangka template bersama: `base.html`, `header.html`, `footer.html` |
| NF-3 | Views melayani HTML dan JSON, karena Flutter di PAS hanya memanggil Django. Kontrak JSON di `off-sdk-evaluation.md` |
| NF-4 | Minimal 50 produk saat deploy |
| NF-5 | Cakupan unit test minimal 80% |
| NF-6 | Aplikasi tetap jalan saat OFF tidak bisa dihubungi |
| NF-7 | Setiap permintaan ke OFF memakai User-Agent di atas, retry pada 5xx, dan lookup dibatasi per pengguna |
| NF-8 | Push ke `main` men-deploy ke PWS lewat GitHub Actions, jadi `main` hanya menerima `dev` yang lulus `check` dan `test` |
| NF-10 | Footer memuat atribusi OFF dan lisensi (ODbL, DbCL, CC BY-SA) dengan tautan ke openfoodfacts.org. Detail produk `source=off` menaut ke halamannya |
| NF-11 | `SECRET_KEY` dari environment tanpa fallback, `DEBUG = not PRODUCTION`, cookie `Secure` dan HSTS 1 jam di produksi. Password lolos validator bawaan dan wajib berisi huruf dan angka. `SECURE_SSL_REDIRECT` dan `SECURE_PROXY_SSL_HEADER` belum dipasang sampai proxy PWS diuji |

## 9. Ukuran keberhasilan

Penilaian: kelima modul terintegrasi, semua tes lulus, cakupan 80%, dan tiap anggota memenuhi tujuh Aturan Khusus. Produk: pengguna baru bisa membuat shelf berisi dua produk dan membaca tabelnya dalam kurang dari satu menit. Target "70% produk hasil seeding punya 4 dari 6 baris" tidak tercapai dengan seeding 406 produk (165 dari 406, 41%), lihat keputusan 16.

## 10. Asumsi

1. Jumlah produk Indonesia di OFF cukup (8.186 sampai 9.001), tapi kelengkapannya tidak.
2. Semua anggota sudah mengerjakan Tutorial 05 dan 06 (AJAX).
3. Server PWS keluar lewat satu IP, sehingga batas OFF dipakai bersama. Belum dicek.
4. Target pengguna (mahasiswa dan pekerja muda yang belanja di minimarket) belum divalidasi.

## 11. Risiko aktif

| Risiko | Penanganan |
|--------|------------|
| Skor kosong untuk hampir semua produk | Estimasi skor lingkungan disimpan terpisah. Produk berdata kosong jadi antrean Modul 4 |
| Produk non-Indonesia masuk lewat lookup atau refresh | `is_sold_in_indonesia()` di ketiga jalur, dengan tes |
| OFF membalas 503 HTML | Retry dengan jeda, timeout 10 detik, data lokal tetap dipakai |
| Batas 15 permintaan per menit dipakai bersama | Lookup 3 per menit per pengguna, hasil disimpan lokal |
| Produk dihapus dan data modul lain ikut hilang | Soft delete dan `PROTECT`. `Decision` memakai `SET_NULL` |
| Refresh menimpa koreksi | Refresh melewati field yang sudah disetujui |
| Akun dikunci pihak iseng | Diterima. Pulihkan dengan `python manage.py axes_reset` |

## 12. Linimasa

Status dan sisa tugas ada di `timeline.md`. Jadwal harian dibahas di grup. Tonggak: auth selesai 4 Okt, Modul 1 di `dev` 20 Okt, deploy pertama dengan katalog 23 Okt, Shelf di `dev` 24 Okt, pengumpulan 30 Okt 23.59 WIB.

## 13. Keputusan

Disetujui kelompok, kecuali yang ditandai belum final. Cakupan: **Kelompok** atau **Modul N**.

| No | Keputusan | Cakupan |
|----|-----------|---------|
| 1 | Nama aplikasi PilihYuk | Kelompok |
| 2 | Lima modul dan pemiliknya mengikuti README | Kelompok |
| 3 | Kurator memakai `is_staff`, tanpa model User kustom | Kelompok |
| 4 | Seeding dari dump yang disaring ke Indonesia. API runtime hanya untuk lookup barcode dan refresh satu produk | Kelompok |
| 5 | `DataCorrection` hanya untuk produk yang sudah ada. Produk baru lewat Modul 1 | Kelompok |
| 7 | Satu suara per pengguna per usulan (`RecommendationVote`) | Modul 3 |
| 8, 9 | Hanya produk Indonesia. Lookup non-Indonesia ditolak, refresh yang kehilangan label dilewati, produk manual dianggap Indonesia | Kelompok |
| 10 | Soft delete lewat `is_active`. Produk yang masih dipakai tidak bisa dihapus | Kelompok |
| 11 | Produk manual tidak di-refresh. Produk OFF di-refresh kecuali field yang koreksinya disetujui | Kelompok |
| 12 | PostgreSQL di produksi, SQLite lokal, tag hanya untuk tampilan | Kelompok |
| 13 | Tidak ada filter tag di Modul 5. Filter label hanya `halal_labeled` | Kelompok |
| 14 | Riwayat produk yang dilihat disimpan di `ProductView` | Modul 1 |
| 15 | Usulan rekomendasi unik pada pasangan produk | Modul 3 |
| 16 | **Seeding, belum final.** Rencana awal: 196 produk dengan minimal 4 dari 6 baris pembanding. Yang dipakai Modul 1: 406 produk dengan Nutri-Score resmi (437 dikurangi 30 tanpa nama dan 1 barcode tidak valid). Dengan aturan awal, 165 dari 406 lolos, dan sekitar 31 dari 196 tidak ikut (kemungkinan yang tanpa Nutri-Score). Belum dicek ke dump | Kelompok |
| 17 | Field Product mengikuti bagian 7 | Kelompok |
| 18 | Tidak ada fork shelf. Diganti "Simpan ke Shelf Saya" (`SavedShelf`) tanpa identitas penyimpan | Modul 2 |
| 19 | Skor lingkungan estimasi disimpan di `environmental_grade_estimated` | Kelompok |
| 20 | `Decision` merujuk ke `Shelf` (`SET_NULL`) dan produk, bukan `ShelfItem` | Modul 5 |
| 21 | Kategori dan merek berupa teks di Product | Modul 1 |
| 22 | Satu pengajuan koreksi untuk satu produk dengan beberapa field, ditinjau per field | Modul 4 |
| 23 | Halaman Shelf Saya bisa dibuka dari halaman jelajah shelf | Modul 2 |
| 24 | Django 5.2 (butuh PostgreSQL 14 ke atas) | Kelompok |
| 25 | Responsif pada pengumpulan final | Kelompok |
| 26 | Atribusi OFF di footer dan tautan "Lihat di Open Food Facts" di detail produk OFF | Kelompok |
| 27 | Lookup barcode dibatasi 3 per menit per pengguna | Kelompok |
| 28 | Tailwind lewat script CDN, tanpa build. Butuh internet | Kelompok |
| 29 | `sodium_100g` (gram, tampil mg) menggantikan garam, dan `carbohydrates_100g` ditambah | Kelompok |
| 31 | Product punya `ingredients_text`, `allergens`, `serving_size`. "Dapat didaur ulang" tidak dipakai | Kelompok |
| 32 | Figma punya frame desktop dan ponsel. Tabel pembanding di ponsel: 2 produk per layar, geser horizontal, kolom metrik menempel | Kelompok |
| 33 | Enam app: `accounts`, `product_catalog`, `shelves`, `substitutions` (branch `recommendations`), `data_correction`, `preferences` | Kelompok |
| 34 | `featured_shelf()` dan `featured_shelves()` di landing diganti query `Shelf` dan `Product` | Modul 1, 2 |
| 36 | Tiap modul punya branch, digabung ke `dev` lalu `main` | Kelompok |
| 37 | Tujuh Aturan Khusus dulu, bonus belakangan | Kelompok |
| 38 | Login dengan email atau username di atas `User` bawaan. Akun dari halaman Daftar memakai email sebagai username | Kelompok |
| 39 | **Tidak dikerjakan:** verifikasi email, masuk dengan Google (dibatalkan 24 Okt), halaman Ketentuan Layanan dan centang persetujuan (dihapus 24 Okt). **Dikerjakan 24 Okt:** reset password (F-0.11), dengan SMTP dari environment | Kelompok |
| 40 | django-axes: 5 gagal per akun, kunci 15 menit, direset saat berhasil | Kelompok |
| 41 | Halaman Profil sebagai hub ke modul lain. Ganti email wajib password | Daffaa |
| 42 | `SECRET_KEY` dari environment, `DEBUG = not PRODUCTION`, `LANGUAGE_CODE = 'id'`, `Procfile` menjalankan `collectstatic` dan `migrate`. Seeding di PWS dijalankan manual | Kelompok |

Nomor 6, 30, dan 35 sudah terserap ke butir lain.

### Belum diputuskan

| No | Hal | Usulan |
|----|-----|--------|
| K-7 | Cache Redis | Tidak dipakai. Bila perlu cache, mulai dari cache bawaan Django (memori lokal atau database) untuk hasil lookup dan tabel shelf publik |
| K-12 | Melengkapi `misc_tags` dan `product_name_id` untuk produk hasil seeding | Sekali lewat API v3 per barcode, atau tunggu refresh pertama |
| K-13 | Frekuensi seeding ulang | Sekali sebelum pengumpulan |

## 14. Belum diverifikasi

1. Apakah proxy PWS meneruskan `X-Forwarded-Proto` dan IP asli. Ini menentukan apakah `SECURE_PROXY_SSL_HEADER`, `SECURE_SSL_REDIRECT`, dan lockout per IP aman dipasang.
2. Apakah PWS keluar lewat satu IP.
3. Kode 429 dari OFF (tidak pernah dipicu, ditangani seperti 503).
4. Penyebab selisih 8.186 (dump) dan 9.001 (API) produk Indonesia.
5. SDK Dart belum dijalankan.
6. Tampilan auth di ponsel sungguhan.
