# Timeline PilihYuk

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB (diundur dari 23 Oktober). Jadwal harian dibahas di grup, jadi dokumen ini hanya mencatat status, pembagian, aturan kerja, dan sisa tugas.

## Status per 24 Oktober

Status branch anggota lain dibaca dari riwayat Git saja (pesan commit, nama file, posisi branch). Kodenya tidak dibuka atau dijalankan, jadi apakah fiturnya berjalan belum dicek.

| Branch | Isi | Posisi |
|--------|-----|--------|
| `main` (PWS) | Auth, Modul 1, halaman bersama, rename Rekomendasi | Ter-deploy 23 Okt. `migrate` jalan lewat `Procfile`, `seed_products` dijalankan manual |
| `dev` | `main` ditambah model `Shelf`, `ShelfItem`, `SavedShelf` | 163 tes lulus (24 Okt) |
| `product_catalog` (Yasmin) | Katalog, lookup barcode, input manual, riwayat lihat, seeding 406 produk | Di `dev`. Dua commit (produk di landing, layout ponsel) belum masuk |
| `shelves` (Daffaa) | CRUD shelf, daftar publik dengan pencarian, Shelf Saya, detail, JSON | Belum di `dev` |
| `recommendations` (Rafael, per 23 Okt) | Model `Substitution`, form, view, template, tes, di folder `substitutions/` | Belum di `dev` |
| `data_correction` (Rayyan, per 23 Okt) | Model, validasi, ajukan dan tinjau koreksi, antrean kurator dan kontribusi, JSON, tes | Belum di `dev`. `data_correction.js` belum diisi |
| `preferences` (Jonathan, per 23 Okt) | Belum ada kode | Model `Shelf` sudah ada, jadi `Decision` bisa ditulis |

## Pembagian

| Modul | Pemilik | App Django | Model |
|-------|---------|------------|-------|
| 1. Katalog Produk | Yasmin | `product_catalog` | `Product`, `ProductView` |
| 2. Shelf dan Tabel Pembanding | Daffaa | `shelves` | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3. Rekomendasi Komunitas | Rafael | `substitutions` (branch `recommendations`) | `Substitution`, `SubstitutionVote` |
| 4. Antrean Data | Rayyan | `data_correction` | `DataCorrection`, `DataCorrectionItem` |
| 5. Preferensi dan Riwayat Keputusan | Jonathan | `preferences` | `Preference`, `Decision` |
| Auth | Daffaa | `accounts` | `User` bawaan Django |

Template ada di `templates/<app>/`, JavaScript di `static/js/<app>.js`, dan semua halaman mewarisi `base.html`. View yang dipakai AJAX juga punya versi JSON untuk Flutter nanti.

## Aturan kerja

- Tiap modul punya branch sendiri. Sebelum PR ke `dev`, jalankan `git merge origin/dev` di branch sendiri, selesaikan konflik, lalu `manage.py check` dan `manage.py test`.
- Push ke `main` langsung men-deploy ke PWS, jadi `main` harus selalu bisa jalan. Daffaa yang menggabungkan `dev` ke `main`.
- Jangan menyunting file modul lain. Kalau perlu, minta pemiliknya atau buka PR kecil terpisah.
- `settings.py` dan `urls.py` cukup diubah satu baris per app. Kalau bentrok, simpan kedua baris.
- Commit atas nama sendiri, di modul sendiri, karena penilaian individu melihat kontribusi per modul.
- Sebelum fitur dibekukan, cek tujuh Aturan Khusus di modul masing-masing: model, view CRUD, template, form, AJAX, pembatasan login, dan filter dari database.
- `LANGUAGE_CODE = 'id'` membuat desimal tampil berkoma ("7,5 g"). Di nilai CSS atau JS, pakai bilangan bulat atau `{{ x|unlocalize }}` setelah `{% load l10n %}`.

## Wajib dulu, bonus belakangan

Tujuh Aturan Khusus yang dinilai, jadi itu dikerjakan lebih dulu. Bonus menyusul kalau sempat:

- Urutan tabel pembanding mengikuti preferensi pengguna (`preferences/ranking.py`). Ini yang paling diutamakan karena disebut README sebagai unsur kebaruan.
- Antrean kontribusi diurutkan dari produk yang paling sering masuk shelf.
- Skor lingkungan estimasi untuk produk tanpa skor resmi.
- Refresh data satu produk dari Open Food Facts.

## Sisa tugas

### Yasmin (`product_catalog`)

- PR dua commit yang belum di `dev`. Commit landing menyentuh `pilihyuk/views.py` dan `templates/index.html`, yang juga sudah diubah di `dev`, jadi pertahankan perubahan dari kedua sisi.
- Rapikan dropdown kategori dan merek (ada isian ganda dan ngawur dari tag OFF).
- Tampilan katalog dan detail masih jauh dari Figma frame 03 dan 04.
- Uji pagination dan filter dengan 406 produk, dan pastikan query tidak lambat.
- Bonus: refresh produk dari OFF tanpa menimpa koreksi yang sudah disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- Gabungkan CRUD shelf ke `dev`.
- Tambah dan keluarkan produk lewat AJAX. Kandidat diambil dari `Product` yang aktif dan bisa difilter. Batas 12 produk dicek di form.
- Tabel pembanding: pilih sampai 4 produk, tampilkan skor, kemasan, asal, dan gizi utama, tandai nilai terbaik, dan biarkan `"unknown"` tampil apa adanya tanpa diperingkat.
- Simpan ke Shelf Saya (`SavedShelf`) lewat AJAX, dengan jumlah penyimpan tanpa identitasnya.
- Isi `featured_shelves()` di landing dengan shelf publik terbaru, setelah commit landing Yasmin masuk.
- Integrasi: nilai `"unknown"` menaut ke formulir koreksi Rayyan, dan tombol "Pilih produk ini" menyimpan `Decision` lewat view Jonathan.
- Sebelum pengumpulan, coba semua alur di PWS sebagai pengunjung, pengguna, dan kurator.
- Bonus: urutan dari `preferences/ranking.py` di tabel pembanding.

### Rafael (`recommendations`)

- PR ke `dev`, dengan URL modul di `/rekomendasi/` karena navbar sudah menaut ke sana.
- Satu baris di `product_detail.html` milik Yasmin perlu disepakati dengannya.
- Belum terlihat di commit: `SubstitutionVote` dan voting lewat AJAX. Satu pengguna satu suara per usulan, bisa diubah atau ditarik, dan jumlahnya dihitung dengan `annotate`.
- Kandidat pengganti disaring dari `Product` menurut kategori dan skor. Pengunjung bisa membaca usulan tanpa melihat pengusulnya.
- Tes: arah usulan, pasangan unik, satu suara per pengguna, dan akses pengunjung.

### Rayyan (`data_correction`)

- PR ke `dev`.
- AJAX kirim dan tinjau di `static/js/data_correction.js`.
- Responsif ponsel, dan akun kurator untuk demo di PWS.
- Bonus: antrean diurutkan dari produk yang paling sering masuk shelf.

### Jonathan (`preferences`)

- `git merge origin/dev` dulu, lalu `migrate`.
- `Preference` (nutrient, direction, weight; unik per pengguna dan nutrien) dan `Decision` (user, shelf dengan `SET_NULL`, product dengan `SET_NULL`, note, created_at).
- CRUD preferensi dengan nutrien terbatas: protein, serat, gula, natrium, lemak jenuh, energi. Pratinjau jumlah produk yang lolos lewat AJAX.
- CRUD riwayat keputusan, hanya untuk pemiliknya. Tombol "Pilih produk ini" di tabel pembanding dikerjakan bersama Daffaa.
- Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.
- Bonus: `preferences/ranking.py` yang mengurutkan produk menurut preferensi, dengan `"unknown"` tidak diperingkat.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 5 baru mulai, Modul 2 belum lengkap | Tujuh Aturan Khusus dulu, bonus belakangan |
| Modul 3 dan 4 besar dan belum pernah digabung dengan modul lain | PR ke `dev` secepatnya supaya konflik dan tes gagal ketahuan lebih awal |
| Konflik di `urls.py`, `base.html`, dan `pilihyuk/views.py` | Satu baris per app dan merge cepat. `base.html` hanya diubah Daffaa |
| Tailwind CDN butuh internet | Pastikan koneksi saat demo |
| Lupa `SECRET_KEY` di `.env` | `manage.py` berhenti dengan `KeyError`. Caranya ada di README |
| Akun terkunci karena salah login berulang (django-axes) | Tunggu 15 menit atau jalankan `python manage.py axes_reset`. Jangan coba-coba akun demo sebelum demo |
| Batas Open Food Facts 15 permintaan per menit | Lookup dibatasi 3 per menit per pengguna. Seeding tidak memanggil API |
| Seseorang tidak sempat | Bilang lebih awal di grup. Yang paling mudah dialihkan: tes, responsif ponsel, dan bonus |
