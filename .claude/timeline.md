# Timeline PilihYuk

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB. Jadwal harian dibahas di grup, jadi dokumen ini hanya mencatat status, pembagian, aturan kerja, dan sisa tugas.

## Status per 24 Oktober

Status branch anggota lain dibaca dari riwayat Git saja, tanpa membuka atau menjalankan kodenya.

| Branch | Isi | Posisi |
|--------|-----|--------|
| `main` (PWS) | Auth, Modul 1, halaman bersama, rename Rekomendasi | Ter-deploy 23 Okt. `seed_products` dijalankan manual |
| `dev` | `main` ditambah CRUD shelf, perubahan login, dan dokumen ini | 175 tes lulus (24 Okt) |
| `product_catalog` (Yasmin) | Katalog, lookup barcode, input manual, riwayat lihat, seeding 406 produk | Di `dev`. Dua commit (produk di landing, layout ponsel) belum masuk |
| `shelves` (Daffaa) | Model dan CRUD shelf | Di `dev`. AJAX produk dan tabel pembanding belum |
| `recommendations` (Rafael, per 23 Okt) | Model `Substitution`, form, view, template, tes, di folder `substitutions/` | Belum di `dev` |
| `data_correction` (Rayyan, per 23 Okt) | Model, ajukan dan tinjau koreksi, antrean kurator dan kontribusi, JSON, tes | Belum di `dev`. `data_correction.js` belum diisi |
| `preferences` (Jonathan, per 23 Okt) | Belum ada kode | `Shelf` sudah ada, jadi `Decision` bisa ditulis |

## Pembagian

| Modul | Pemilik | App Django | Model |
|-------|---------|------------|-------|
| 1. Katalog Produk | Yasmin | `product_catalog` | `Product`, `ProductView` |
| 2. Shelf dan Tabel Pembanding | Daffaa | `shelves` | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3. Rekomendasi Komunitas | Rafael | `substitutions` (branch `recommendations`) | `Substitution`, `SubstitutionVote` |
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

- Urutan tabel pembanding mengikuti preferensi pengguna (`preferences/ranking.py`). Paling diutamakan.
- Antrean kontribusi diurutkan dari produk yang paling sering masuk shelf.
- Skor lingkungan estimasi.
- Refresh data satu produk dari Open Food Facts.

## Sisa tugas

### Yasmin (`product_catalog`)

- PR dua commit yang belum di `dev`. Commit landing menyentuh `pilihyuk/views.py` dan `templates/index.html`, jadi pertahankan perubahan dari kedua sisi.
- Catatan: path sampel di `product_catalog/fixture_data.py` dan `fixtures/README.md` sudah diubah ke `.claude/off-samples/` (24 Okt), karena folder `pilihyuk-docs/` diratakan.
- Rapikan dropdown kategori dan merek (ada isian ganda dan ngawur dari tag OFF).
- Sesuaikan katalog dan detail dengan Figma frame 03 dan 04.
- Bonus: refresh produk tanpa menimpa koreksi yang disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- Tambah dan keluarkan produk lewat AJAX, dengan kandidat yang bisa difilter dan batas 12 produk.
- Tabel pembanding: sampai 4 produk, skor, kemasan, asal, gizi utama, penanda nilai terbaik, dan `"unknown"` tanpa peringkat.
- Simpan ke Shelf Saya lewat AJAX.
- Isi `featured_shelves()` di landing setelah commit landing Yasmin masuk.
- Integrasi: `"unknown"` menaut ke koreksi Rayyan, dan tombol "Pilih produk ini" menyimpan `Decision` lewat view Jonathan.
- Coba semua alur di PWS sebelum pengumpulan.
- Reset password sudah jalan. Untuk PWS, isi `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` di environment. Bonus: urutan dari `preferences/ranking.py`.

### Rafael (`recommendations`)

- PR ke `dev`, dengan URL modul di `/rekomendasi/`.
- Sepakati satu baris di `product_detail.html` dengan Yasmin.
- `SubstitutionVote` dan voting lewat AJAX: satu suara per pengguna per usulan, bisa diubah atau ditarik, dihitung dengan `annotate`.
- Kandidat pengganti difilter menurut kategori dan skor. Pengunjung tidak melihat pengusul.
- Tes: arah usulan, pasangan unik, satu suara per pengguna, akses pengunjung.

### Rayyan (`data_correction`)

- PR ke `dev`.
- AJAX kirim dan tinjau di `static/js/data_correction.js`.
- Responsif ponsel dan akun kurator untuk demo.
- Bonus: antrean diurutkan dari produk yang paling sering masuk shelf.

### Jonathan (`preferences`)

- `git merge origin/dev`, lalu `migrate`.
- `Preference` (nutrient, direction, weight; unik per pengguna dan nutrien) dan `Decision` (shelf dan product dengan `SET_NULL`, note, created_at).
- CRUD preferensi untuk protein, serat, gula, natrium, lemak jenuh, dan energi, dengan pratinjau jumlah produk lewat AJAX.
- CRUD riwayat keputusan, hanya untuk pemiliknya. Tombol "Pilih produk ini" dikerjakan bersama Daffaa.
- Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.
- Bonus: `preferences/ranking.py`, dengan `"unknown"` tidak diperingkat.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 5 baru mulai, Modul 2 belum lengkap | Tujuh Aturan Khusus dulu, bonus belakangan |
| Modul 3 dan 4 belum pernah digabung | PR ke `dev` secepatnya supaya konflik ketahuan lebih awal |
| Konflik di `urls.py`, `base.html`, `pilihyuk/views.py` | Satu baris per app, merge cepat. `base.html` hanya diubah Daffaa |
| Tailwind CDN butuh internet | Pastikan koneksi saat demo |
| Akun terkunci karena salah login berulang | Tunggu 15 menit atau `python manage.py axes_reset` |
| Seseorang tidak sempat | Bilang lebih awal. Yang mudah dialihkan: tes, responsif ponsel, bonus |
