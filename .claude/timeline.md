# Timeline PilihYuk

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB. Jadwal harian dibahas di grup, jadi dokumen ini hanya mencatat status, pembagian, aturan kerja, dan sisa tugas.

## Status per 28 Oktober (sore)

Status branch anggota lain dibaca dari riwayat Git saja, tanpa membuka atau menjalankan kodenya.

| Branch | Isi | Posisi |
|--------|-----|--------|
| `main` (PWS) | Auth, Modul 1, Modul 2, Modul 3, halaman bersama | Ter-deploy 27 Okt (PR #9). Env email terisi, reset password terkirim |
| `dev` | Kelima modul, integrasi tabel dengan preferensi dan koreksi, landing dengan shelf asli, waktu sesuai zona pengguna, dan dokumen ini | 506 tes lulus (28 Okt). Modul 4 dan 5 belum di `main` |
| `product_catalog` (Yasmin) | Katalog, lookup barcode, input manual, riwayat lihat, seeding 406 produk | Di `dev`, termasuk landing dan layout ponsel |
| `shelves` (Daffaa) | CRUD shelf (HTML dan JSON), tambah dan keluarkan produk lewat AJAX, tabel pembanding, penanda Estimasi, Simpan ke Shelf Saya, urutan dari preferensi, tombol Pilih ini | Di `dev` |
| `recommendations` (Rafael) | App `recommendations`, model `Recommendation` dan `RecommendationVote`, daftar, usulan, detail, tes | Di `dev` (PR #8, 27 Okt). Belum ada voting, edit, hapus, dan `recommendations.js` masih kosong |
| `data_correction` (Rayyan, per 27 Okt) | Ajukan dan tinjau koreksi, antrean kurator dan kontribusi, AJAX di semua halaman, frekuensi shelf, tes | Di `dev` (28 Okt) |
| `preferences` (Jonathan) | Preferensi dengan pratinjau AJAX, `Decision` privat, ranking berbobot, riwayat, tes | Di `dev` (PR #10, 27 Okt) |

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

- Urutan tabel pembanding mengikuti preferensi pengguna. Sudah ada (28 Okt).
- Antrean kontribusi diurutkan dari produk yang paling sering masuk shelf.
- Skor lingkungan estimasi.
- Refresh data satu produk dari Open Food Facts.

## Sisa tugas

### Yasmin (`product_catalog`)

- Commit landing dan layout ponsel sudah di `dev`. Commit landing menyentuh `pilihyuk/views.py` (juga diubah Modul 3) dan `templates/index.html`, jadi pertahankan perubahan dari kedua sisi.
- Catatan: path sampel di `product_catalog/fixture_data.py` dan `fixtures/README.md` sudah diubah ke `.claude/off-samples/` (24 Okt), karena folder `pilihyuk-docs/` diratakan.
- Rapikan dropdown kategori dan merek (ada isian ganda dan ngawur dari tag OFF).
- Sesuaikan katalog dan detail dengan Figma frame 03 dan 04.
- Bonus: refresh produk tanpa menimpa koreksi yang disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- Integrasi selesai (28 Okt): urutan dari preferensi, tombol "Pilih ini", dan tautan "Bantu lengkapi data" ke koreksi Rayyan. Landing memakai shelf publik asli.
- Coba semua alur di PWS sebelum pengumpulan.
- Gabungkan `dev` ke `main` supaya Modul 5 ikut live, lalu buat 2 sampai 3 shelf publik sebagai data demo di PWS.

### Rafael (`recommendations`)

- Sepakati satu baris di `product_detail.html` dengan Yasmin.
- Voting lewat AJAX dengan `RecommendationVote` (Aturan Khusus nomor 5), plus view edit dan hapus usulan: satu suara per pengguna per usulan, bisa diubah atau ditarik, dihitung dengan `annotate`.
- Kandidat pengganti difilter menurut kategori dan skor. Pengunjung tidak melihat pengusul.
- Tes: arah usulan, pasangan unik, satu suara per pengguna, akses pengunjung.

### Rayyan (`data_correction`)

- Sudah di `dev`. Rute modul ini sudah diawali `antrean/` dan `moderasi/`, jadi `pilihyuk/urls.py` cukup memuatnya sekali di `''`.
- Akun kurator untuk demo.

### Jonathan (`preferences`)

- Sudah di `dev`. Tombol "Pilih ini" (kirim `compared_product_ids`) dan urutan baris dari preferensi sudah dipasang di Modul 2 pada 28 Okt.
- Perbarui `preferences/NOTES.md`, yang masih menyebut integrasi Shelf belum dipasang.
- Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 3 belum punya voting AJAX, edit, dan hapus | Selesaikan sebelum 30 Okt, karena Aturan Khusus nomor 5 dinilai per anggota |
| Konflik di `urls.py`, `base.html`, `pilihyuk/views.py` | Satu baris per app, merge cepat. `base.html` hanya diubah Daffaa |
| Tailwind CDN butuh internet | Pastikan koneksi saat demo |
| Akun terkunci karena salah login berulang | Tunggu 15 menit atau `python manage.py axes_reset` |
| Seseorang tidak sempat | Bilang lebih awal. Yang mudah dialihkan: tes, responsif ponsel, bonus |
