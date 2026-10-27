# Timeline PilihYuk

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB. Jadwal harian dibahas di grup, jadi dokumen ini hanya mencatat status, pembagian, aturan kerja, dan sisa tugas.

## Status per 27 Oktober

Status branch anggota lain dibaca dari riwayat Git saja, tanpa membuka atau menjalankan kodenya.

| Branch | Isi | Posisi |
|--------|-----|--------|
| `main` (PWS) | Auth, Modul 1, halaman bersama, rename Rekomendasi | Ter-deploy 23 Okt. `seed_products` dijalankan manual |
| `dev` | `main` ditambah Modul 2, Modul 3, perubahan login, favicon, halaman 404, dan dokumen ini | 208 tes lulus (27 Okt). `main` tertinggal 21 commit |
| `product_catalog` (Yasmin) | Katalog, lookup barcode, input manual, riwayat lihat, seeding 406 produk | Di `dev`. Empat commit (produk di landing, layout ponsel, 25 Okt) belum masuk |
| `shelves` (Daffaa) | CRUD shelf, tambah dan keluarkan produk lewat AJAX, tabel pembanding, penanda Estimasi, Simpan ke Shelf Saya | Di `dev` |
| `recommendations` (Rafael) | App `recommendations`, model `Recommendation` dan `RecommendationVote`, daftar, usulan, detail, tes | Di `dev` (PR #8, 27 Okt). Belum ada voting, edit, hapus, dan `recommendations.js` masih kosong |
| `data_correction` (Rayyan, per 27 Okt) | Ajukan dan tinjau koreksi, antrean kurator dan kontribusi, AJAX di semua halaman, frekuensi shelf, tes | Belum di `dev` (39 commit) |
| `preferences` (Jonathan, per 26 Okt) | Preferensi dengan pratinjau AJAX, `Decision` privat, ranking berbobot, riwayat, tes | Belum di `dev` (30 commit) |

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

- Urutan tabel pembanding mengikuti preferensi pengguna (`preferences/ranking.py`). Paling diutamakan. Baris tabel berasal dari `comparison_rows()` di `shelves/comparison.py`, jadi cukup urutkan ulang list itu.
- Antrean kontribusi diurutkan dari produk yang paling sering masuk shelf.
- Skor lingkungan estimasi.
- Refresh data satu produk dari Open Food Facts.

## Sisa tugas

### Yasmin (`product_catalog`)

- PR empat commit yang belum di `dev`, setelah `git merge origin/dev`. Commit landing menyentuh `pilihyuk/views.py` (juga diubah Modul 3) dan `templates/index.html`, jadi pertahankan perubahan dari kedua sisi.
- Commit 25 Okt menulis ke `.claude/pilihyuk-docs/HANDOFF.md`. Folder itu sudah diratakan, jadi pindahkan isinya ke `.claude/HANDOFF.md` atau hapus file itu.
- Catatan: path sampel di `product_catalog/fixture_data.py` dan `fixtures/README.md` sudah diubah ke `.claude/off-samples/` (24 Okt), karena folder `pilihyuk-docs/` diratakan.
- Rapikan dropdown kategori dan merek (ada isian ganda dan ngawur dari tag OFF).
- Sesuaikan katalog dan detail dengan Figma frame 03 dan 04.
- Bonus: refresh produk tanpa menimpa koreksi yang disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- Isi `featured_shelves()` di landing setelah commit landing Yasmin masuk.
- Penanda "Estimasi" untuk Green-Score di tabel pembanding.
- Integrasi: `"unknown"` menaut ke koreksi Rayyan, dan tombol "Pilih produk ini" menyimpan `Decision` lewat view Jonathan.
- Coba semua alur di PWS sebelum pengumpulan.
- Reset password sudah jalan. Untuk PWS, isi `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` di environment. Bonus: urutan dari `preferences/ranking.py`.

### Rafael (`recommendations`)

- Sepakati satu baris di `product_detail.html` dengan Yasmin.
- Voting lewat AJAX dengan `RecommendationVote` (Aturan Khusus nomor 5), plus view edit dan hapus usulan: satu suara per pengguna per usulan, bisa diubah atau ditarik, dihitung dengan `annotate`.
- Kandidat pengganti difilter menurut kategori dan skor. Pengunjung tidak melihat pengusul.
- Tes: arah usulan, pasangan unik, satu suara per pengguna, akses pengunjung.

### Rayyan (`data_correction`)

- Menurut pesan commit, AJAX di semua halaman dan bonus urutan dari frekuensi shelf sudah ada.
- `git merge origin/dev`, lalu PR ke `dev`.
- Akun kurator untuk demo.

### Jonathan (`preferences`)

- Menurut pesan commit, model, CRUD preferensi dengan pratinjau AJAX, riwayat keputusan, dan ranking berbobot sudah ada.
- `git merge origin/dev`, lalu PR ke `dev`.
- Setelah masuk `dev`: tombol "Pilih ini" di tabel pembanding dan urutan baris dari ranking, dikerjakan bersama Daffaa.
- Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 4 dan 5 belum digabung ke `dev` | PR secepatnya setelah `git merge origin/dev`. Konflik di `pilihyuk/urls.py` cukup simpan kedua baris |
| Konflik di `urls.py`, `base.html`, `pilihyuk/views.py` | Satu baris per app, merge cepat. `base.html` hanya diubah Daffaa |
| Tailwind CDN butuh internet | Pastikan koneksi saat demo |
| Akun terkunci karena salah login berulang | Tunggu 15 menit atau `python manage.py axes_reset` |
| Seseorang tidak sempat | Bilang lebih awal. Yang mudah dialihkan: tes, responsif ponsel, bonus |
