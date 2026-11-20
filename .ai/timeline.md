# Timeline PilihYuk

## Proyek Akhir Semester (mulai 17 November)

Aplikasi Flutter ada di repo terpisah `PBP-Kelompok-B4/PilihYuk-Mobile`. API Django REST Framework (DRF) ditulis di repo ini.

- Checkpoint 1: Jumat, 20 November 2026, 23.59 WIB. Endpoint tiap modul sudah jalan di PWS, dan halaman tiap modul bisa dibuka dari drawer.
- Tenggat akhir: Rabu, 9 Desember 2026, 23.59 WIB, tanpa perpanjangan. APK di GitHub Release dan Bitrise.
- Status 20 November: API auth, preferensi, dan shelf sudah ada di `dev`, tetapi belum jalan di PWS karena deploy `main` terakhir dibatalkan. API produk, rekomendasi, dan antrean data belum di-push. Di repo mobile, `dev` berisi kerangka dan halaman Shelf.

### Branch

- Web: setiap anggota memakai lagi branch modul lamanya. Jalankan `git merge origin/main` dulu, lalu PR ke `dev`.
- Mobile: `main`, `dev`, dan branch modul baru dengan nama yang sama (`product_catalog`, `shelves`, `recommendations`, `data_correction`, `preferences`). Buat dari `main`, lalu PR ke `dev`.

### Konvensi API

- Ikuti pola Tutorial 07: `serializers.py`, `api_views.py`, `api_urls.py`, dan `tests_api.py` di app masing-masing. View memakai `@api_view`, `@authentication_classes([SessionAuthentication])`, dan `@permission_classes`, tanpa `@csrf_exempt`.
- `api_urls.py` tiap app sudah dibuat dan sudah dimuat di `pilihyuk/urls.py`, jadi file itu tidak perlu disentuh. Prefix: `/api/v1/products/`, `/api/v1/shelves/`, `/api/v1/recommendations/`, `/api/v1/corrections/`, `/api/v1/preferences/` (termasuk keputusan).
- Auth untuk aplikasi ada di `/api/v1/auth/` (`login/`, `register/`, `logout/`). Ketiganya memakai `authentication_classes([])`, jadi tidak butuh token CSRF.
- Menulis data memakai kata kerja REST biasa: POST untuk membuat (201), PUT atau PATCH untuk mengubah (200), DELETE untuk menghapus (204), dan galat validasi 400. View tulis memakai `SessionAuthentication` dan permission seperti `IsAuthenticated`, tanpa `@csrf_exempt`.
- Di aplikasi, GET memakai `request.get`. Semua POST, PUT, PATCH, dan DELETE ke endpoint yang butuh login memakai `sendJson(request, 'PUT', url, data)` dari `lib/api.dart`. `pbp_django_auth` 0.4.0 tidak mengirim token CSRF dan tidak punya PUT atau DELETE, jadi `sendJson` mengambil token dari cookie `csrftoken` (dipasang Django saat login), mengirimnya sebagai `X-CSRFToken`, dan menambahkan `Referer` yang dicek Django di HTTPS. `request.post` dan `request.postJson` ke endpoint ini akan ditolak 403.

### Tugas per orang

| Anggota | Branch web | Checkpoint 1 web | Branch mobile | Checkpoint 1 mobile |
|---------|------------|------------------|---------------|---------------------|
| Yasmin | `product_catalog` | GET daftar produk (dengan pencarian) dan detail | `product_catalog` | Halaman Katalog |
| Daffaa | `dev`, lalu `shelves` | DRF dan API auth (selesai 17 Nov), GET daftar shelf (selesai 20 Nov) | `main`, lalu `shelves` | Kerangka, login, drawer, README (selesai 17 Nov), halaman Shelf (selesai 20 Nov) |
| Rafael | `recommendations` | GET daftar dan detail rekomendasi | `recommendations` | Halaman Rekomendasi |
| Rayyan | `data_correction` | GET antrean kontribusi | `data_correction` | Halaman Antrean Data |
| Jonathan | `preferences` | GET preferensi dan keputusan milik pengguna | `preferences` | Halaman Preferensi |

Halaman placeholder tiap modul sudah ada di `lib/screens/<modul>/<modul>_page.dart` dan sudah tersambung ke drawer. Ganti isinya tanpa mengganti nama kelasnya. Model Dart masuk ke `lib/models/<modul>.dart`. `main.dart`, `config.dart`, dan `widgets/left_drawer.dart` dipegang Daffaa. Lingkup sampai 9 Desember per modul ada di README repo mobile.

## Proyek Tengah Semester (selesai)

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB. Jadwal harian dibahas di grup, jadi dokumen ini hanya mencatat status, pembagian, aturan kerja, dan sisa tugas.

## Status per 31 Oktober

Status branch anggota lain dibaca dari riwayat Git saja, tanpa membuka atau menjalankan kodenya.

| Branch | Isi | Posisi |
|--------|-----|--------|
| `main` (PWS) | Kelima modul dan halaman bersama | Ter-deploy 28 Okt. Belum ada shelf publik di PWS |
| `dev` | `main` ditambah `SECURE_PROXY_SSL_HEADER`, Modul 3 lengkap, dan perbaikan 29 sampai 30 Okt | 525 tes lulus. PR ke `main` belum tercatat merge |
| `product_catalog` (Yasmin) | Katalog, lookup barcode, input manual, riwayat lihat, seeding 406 produk | Di `dev`, termasuk landing dan layout ponsel |
| `shelves` (Daffaa) | CRUD shelf (HTML dan JSON), tambah dan keluarkan produk lewat AJAX, tabel pembanding, penanda Estimasi, Simpan ke Shelf Saya, urutan dari preferensi, tombol Pilih ini | Di `dev` |
| `recommendations` (Rafael) | Model `Recommendation` dan `RecommendationVote`, daftar (cari, urut, paginasi), usulan, detail, voting, edit, hapus, JSON | Di `dev` (PR #8 dan #15). Belum diaudit ulang terhadap tujuh Aturan Khusus |
| `data_correction` (Rayyan) | Ajukan dan tinjau koreksi, antrean kurator dan kontribusi, AJAX di semua halaman, frekuensi shelf, tes | Di `dev` |
| `preferences` (Jonathan) | Preferensi dengan pratinjau AJAX, `Decision` privat, ranking berbobot, riwayat di `/keputusan/`, tes | Di `dev` (PR #10) |

## Pembagian

| Modul | Pemilik | App Django | Model |
|-------|---------|------------|-------|
| 1. Katalog Produk | Yasmin | `product_catalog` | `Product`, `ProductView` |
| 2. Shelf dan Tabel Pembanding | Daffaa | `shelves` | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3. Rekomendasi Komunitas | Rafael | `recommendations` | `Recommendation`, `RecommendationVote` |
| 4. Antrean Data | Rayyan | `data_correction` | `DataCorrection`, `DataCorrectionItem` |
| 5. Preferensi dan Riwayat Keputusan | Jonathan | `preferences` | `Preference`, `Decision` |
| Auth | Daffaa | `accounts` | `User` bawaan Django |

Template di `templates/<app>/`, JavaScript di `static/js/<app>.js`, semua halaman mewarisi `base.html`, dan view AJAX juga punya versi JSON.

## Aturan kerja

- Sebelum PR ke `dev`, jalankan `git merge origin/dev` di branch sendiri, selesaikan konflik, lalu `manage.py check` dan `manage.py test`.
- Push ke `main` langsung men-deploy ke PWS, jadi `main` harus selalu bisa jalan. Daffaa yang menggabungkan `dev` ke `main`.
- Jangan menyunting file modul lain. Minta pemiliknya, atau buka PR kecil terpisah.
- `settings.py` dan `urls.py` cukup diubah satu baris per app. Kalau bentrok, simpan kedua baris.
- Commit atas nama sendiri, di modul sendiri, karena penilaian individu melihat kontribusi per modul.
- Sebelum fitur dibekukan, cek tujuh Aturan Khusus di modul masing-masing.
- `LANGUAGE_CODE = 'id'` membuat desimal berkoma ("7,5 g"). Di nilai CSS atau JS, pakai bilangan bulat atau `{{ x|unlocalize }}` setelah `{% load l10n %}`.

## Bonus (setelah bagian wajib beres)

- Urutan tabel pembanding mengikuti preferensi pengguna. Sudah ada.
- Antrean kontribusi diurutkan dari produk yang paling sering masuk shelf.
- Skor lingkungan estimasi.
- Refresh data satu produk dari Open Food Facts.

## Sisa tugas

### Yasmin (`product_catalog`)

- Landing menyentuh `pilihyuk/views.py` (juga diubah Modul 3) dan `templates/index.html`, jadi pertahankan perubahan dari kedua sisi.
- Path sampel OFF kini `.ai/product_catalog/helpers/off-samples/`, dibaca `product_catalog/seed/fixture_data.py`. Pada 31 Okt kode seed dan mapping OFF dipindah ke `product_catalog/seed/`, dan tes selain `tests.py` ke `product_catalog/test_suites/`. Tarik `dev` sebelum menyunting berkas di sana.
- Rapikan dropdown kategori dan merek (ada isian ganda dan ngawur dari tag OFF).
- Sesuaikan katalog dan detail dengan Figma frame 03 dan 04.
- Bonus: refresh produk tanpa menimpa koreksi yang disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- Integrasi selesai: urutan dari preferensi, tombol "Pilih ini", tautan ke koreksi Rayyan, dan landing dengan shelf publik asli.
- Coba semua alur di PWS, gabungkan `dev` ke `main`, lalu buat 2 sampai 3 shelf publik sebagai data demo.
- 29 sampai 30 Okt, atas permintaan, Daffaa menyunting file modul lain: `recommendations/` (larangan memilih usulan sendiri, produk nonaktif disembunyikan, vote atomik, daftar dengan cari, urut, paginasi, dan nama pembuat khusus pengguna login), `preferences/` (rute `/riwayat/` menjadi `/keputusan/`, hapus massal menjawab 404 untuk ID milik orang lain, tes dan `NOTES.md` disesuaikan). Rafael dan Jonathan perlu menarik `dev` dan memeriksa perubahan itu sebelum merge.

### Rafael (`recommendations`)

- Voting, edit, dan hapus sudah ada (PR #15).
- Uji paginasi `/rekomendasi/` dengan data banyak dan periksa modul terhadap tujuh Aturan Khusus.
- Sepakati satu baris di `product_detail.html` dengan Yasmin.

### Rayyan (`data_correction`)

- Sudah di `dev`. Rute modul ini diawali `antrean/` dan `moderasi/`, jadi `pilihyuk/urls.py` memuatnya sekali di `''`.
- Akun kurator untuk demo.

### Jonathan (`preferences`)

- Sudah di `dev`. Tombol "Pilih ini" dan urutan baris dari preferensi sudah dipasang di Modul 2.
- Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 3 belum diaudit ulang terhadap tujuh Aturan Khusus | Audit sebelum pengumpulan, karena Aturan Khusus dinilai per anggota |
| Konflik di `urls.py`, `base.html`, `pilihyuk/views.py` | Satu baris per app, merge cepat. `base.html` hanya diubah Daffaa |
| Tailwind CDN butuh internet | Pastikan koneksi saat demo |
| Akun terkunci karena salah login berulang | Tunggu 15 menit atau `python manage.py axes_reset` |
| Seseorang tidak sempat | Bilang lebih awal. Yang mudah dialihkan: tes, responsif ponsel, bonus |
