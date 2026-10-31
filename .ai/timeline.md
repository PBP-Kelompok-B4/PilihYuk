# Timeline PilihYuk

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
