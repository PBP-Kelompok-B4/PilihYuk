# Timeline PilihYuk

Tenggat: Jumat, 30 Oktober 2026, 23.59 WIB (diundur dari 23 Oktober). Dokumen ini untuk kelompok dan ikut di-commit di folder `.claude/`.

Jadwal harian tidak ditulis di sini, karena dibahas langsung di grup. Dokumen ini mencatat status, pembagian, aturan kerja, dan tugas yang tersisa.

## Status per 23 Oktober

Dibaca dari riwayat Git di GitHub (pesan commit, nama file yang berubah, dan posisi branch), tanpa membuka atau menjalankan kode branch lain. Apakah fitur benar berjalan dan tesnya lulus belum dicek.

| Branch | Isi menurut commit | Posisi |
|--------|--------------------|--------|
| `main` (deploy PWS) | Scaffold, landing page, Tailwind CDN, auth (PR #1), dokumen tim (PR #2) | Terakhir 6 Okt. Belum memuat modul apa pun selain auth |
| `dev` | `main` ditambah Modul 1 (PR #4, digabung 20 Okt) | 5 commit di depan `main` |
| `product_catalog` (Yasmin) | Model `Product` dan `ProductView`, klien OFF, lookup barcode dengan kuota, input manual, riwayat lihat, daftar dan detail, seeding 406 produk yang sudah ditinjau, tes | Sudah di `dev`. Dua commit belum masuk `dev`: produk katalog di landing page (menyentuh `pilihyuk/views.py`, `templates/index.html`, `pilihyuk/tests.py`) dan "temporary mobile layout" |
| `shelves` (Daffaa) | Belum ada kode modul. `shelves/` masih hasil scaffold | Belum mulai |
| `recommendations` (Rafael) | Model `Substitution` dengan migrasi, form, view, URL, template daftar, detail, dan form, tes, dan satu baris di `templates/product_catalog/product_detail.html`. Kodenya masih di folder app `substitutions/` | Belum di `dev`. Branch lama `substitutions` kosong |
| `data_correction` (Rayyan) | Model `DataCorrection` dan `DataCorrectionItem` dengan migrasi, validasi dan konversi satuan, layanan ajukan, tarik, setujui, tolak, form multi-field, halaman pengajuan saya, antrean kurator dengan tinjauan per field, antrean kontribusi dengan filter, respons HTML dan JSON, tes | Belum di `dev`. `static/js/data_correction.js` belum berubah |
| `preferences` (Jonathan) | Hanya sinkron dari `dev` dan perubahan `.gitignore` | Belum mulai. Tertinggal 4 commit dari `dev` |

Akibatnya:

- `Decision` milik Jonathan butuh model `Shelf`, jadi model `Shelf` adalah penghambat utama.
- Di PWS baru ada auth. Modul 1 belum pernah dicoba di PostgreSQL, dan `Procfile` release belum pernah benar-benar diuji.

## Pembagian

| Modul | Pemilik | App Django | Model |
|-------|---------|------------|-------|
| 1. Katalog Produk | Yasmin | `product_catalog` | `Product`, `ProductView` |
| 2. Shelf dan Tabel Pembanding | Daffaa | `shelves` | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3. Rekomendasi Komunitas | Rafael | `substitutions` (branch `recommendations`) | `Substitution`, `SubstitutionVote` |
| 4. Antrean Data | Rayyan | `data_correction` | `DataCorrection`, `DataCorrectionItem` |
| 5. Preferensi dan Riwayat Keputusan | Jonathan | `preferences` | `Preference`, `Decision` |
| Auth | Daffaa | `accounts` | memakai `User` bawaan Django |

Template tiap modul masuk `templates/<app>/`, JavaScript-nya ke `static/js/<app>.js`, dan semua halaman mewarisi `base.html`. View yang dipakai AJAX juga punya versi JSON, karena Flutter nanti memakainya.

## Aturan kerja

- Alur branch: tiap modul punya branch sendiri, lalu digabung ke `dev` untuk diuji bersama (`manage.py check` dan `manage.py test`), lalu `dev` di-push ke `main`. Push ke `main` sekaligus deploy ke PWS lewat GitHub Actions, jadi `main` harus selalu bisa jalan.
- Sebelum PR ke `dev`: `git merge dev` ke branch sendiri, selesaikan konflik di sana, lalu jalankan `check` dan `test`.
- Jangan menyunting file milik modul lain. Kalau perlu perubahan di sana, minta pemiliknya atau buka PR kecil terpisah.
- `settings.py` dan `urls.py` hanya diubah satu baris per app. Kalau bentrok saat merge, simpan kedua baris.
- Commit atas nama sendiri, di modul sendiri. Penilaian individu melihat kontribusi per modul.
- Daffaa yang mendorong `dev` ke `main`.
- Tailwind jalan lewat script CDN, jadi tidak ada langkah build.
- Sebelum fitur dibekukan, setiap pemilik modul mencentang tujuh Aturan Khusus untuk modulnya: model, view CRUD, template, form, AJAX, pembatasan login, dan filter dari database.
- `LANGUAGE_CODE = 'id'` membuat desimal di template tampil berkoma ("7,5 g"). Float di dalam nilai CSS atau JS (`style="width: {{ x }}%"`) jadi rusak, jadi pakai bilangan bulat atau `{{ x|unlocalize }}` setelah `{% load l10n %}`.

## Wajib dulu, bonus belakangan

Tiap modul menyelesaikan tujuh Aturan Khusus lebih dulu. Itu yang dinilai. Bonus dikerjakan hanya kalau bagian wajib sudah beres:

- Urutan tabel pembanding mengikuti preferensi pengguna (`preferences/ranking.py` dipasang di tabel). Ini bonus yang paling diutamakan, karena disebut di README sebagai unsur kebaruan.
- Antrean kontribusi diurutkan dari produk yang paling sering ada di shelf.
- Skor lingkungan estimasi untuk produk yang skor resminya kosong.
- Refresh data satu produk dari Open Food Facts.

## Tugas per orang

### Yasmin (`product_catalog`)

- PR dua commit yang belum di `dev` (landing page dan tampilan ponsel). Commit landing page menyentuh file bersama, jadi kabari Daffaa.
- Tautan "Lihat di Open Food Facts" dan atribusi di halaman detail. Cek `templates/components/footer.html` memuat lisensi ODbL dan CC BY-SA.
- Uji pagination dan filter dengan data seeding lengkap, dan pastikan query tidak lambat (`select_related`).
- Responsif ponsel untuk `templates/product_catalog/`.
- Pastikan seeding 406 produk berjalan di PostgreSQL PWS bersama Daffaa.
- Bonus: refresh data satu produk dari Open Food Facts yang melewati field dengan `DataCorrectionItem` disetujui, dan skor lingkungan estimasi.

### Daffaa (`shelves`, `accounts`, integrasi)

- `shelves/models.py`: `Shelf`, `ShelfItem`, `SavedShelf`, dengan batas 12 produk divalidasi di form. Gabungkan ke `dev` lebih dulu, karena `Decision` milik Jonathan membutuhkannya.
- CRUD shelf: nama, konteks toko, deskripsi, publik atau privat. Hanya pemilik yang bisa menyunting dan menghapus. Shelf privat hanya tampil bagi pemiliknya.
- Tambah dan keluarkan produk dari shelf lewat AJAX. Kandidat produk disaring dari `Product` dan hanya yang aktif.
- Tabel pembanding: pilih sampai 4 produk dari shelf, tampilkan Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama, penanda nilai terbaik, dan `"unknown"` apa adanya tanpa diperingkat. Template di `templates/shelves/compare.html`, urutan ulang lewat `static/js/shelves.js`.
- "Simpan ke Shelf Saya" (`SavedShelf`) dan halaman "Shelf Saya": shelf sendiri dan shelf publik orang lain yang disimpan. Identitas penyimpan tidak tampil.
- Landing page: isi `featured_shelves()` di `pilihyuk/views.py` dengan shelf publik terbaru, setelah commit landing page Yasmin masuk `dev`.
- Tes di `shelves/tests.py`: batas 12 produk, hak akses shelf, dan `SavedShelf`.
- Integrasi: tautkan nilai `"unknown"` di tabel pembanding ke formulir koreksi Rayyan, pasang tombol "Pilih produk ini" yang menyimpan `Decision` lewat view Jonathan, dan tabel pembanding di ponsel (dua produk per layar, scroll horizontal).
- Deploy: dorong `dev` ke `main`, baca log deploy, pastikan migrasi dan `collectstatic` berjalan. Sebelum pengumpulan, jalankan semua alur di PWS sebagai pengunjung, pengguna, dan kurator.
- Bonus: pasang urutan dari `preferences/ranking.py` ke tabel pembanding untuk pengguna yang login.

### Rafael (`recommendations`)

- PR branch `recommendations` ke `dev`.
- Baris di `templates/product_catalog/product_detail.html` ada di file Yasmin, jadi sepakati dengannya.
- Belum terlihat dari commit: `SubstitutionVote` dan suara lewat AJAX di `static/js/substitutions.js`. Satu pengguna satu suara per usulan, bisa diubah atau ditarik, jumlah suara dihitung dengan `annotate`.
- Filter dari database: kandidat pengganti disaring menurut kategori dan skor dari `Product`. Pengunjung bisa membaca usulan tanpa melihat siapa pengusulnya.
- Responsif ponsel untuk `templates/substitutions/`.
- Tes di `substitutions/tests.py`: arah usulan, unik pasangan, satu suara per pengguna, dan akses pengunjung.
- Bantu Daffaa menguji alur di PWS.

### Rayyan (`data_correction`)

- PR ke `dev`. Branch sudah memuat `dev` terbaru.
- AJAX untuk kirim dan tinjau di `static/js/data_correction.js` (file ini belum berubah).
- Responsif ponsel untuk `templates/data_correction/`.
- Siapkan akun kurator untuk demo di PWS.
- Bonus: antrean diurutkan dari produk yang paling sering ada di shelf (setelah `ShelfItem` ada), dan persetujuan koreksi tidak tertimpa refresh.

### Jonathan (`preferences`)

- Gabungkan `dev` terbaru ke branch `preferences` dulu (tertinggal 4 commit).
- `preferences/models.py`: `Preference` (nutrient, direction, weight; unik per pengguna dan nutrien) dan `Decision` (user, shelf, product, note, created_at). `Preference` bisa langsung ditulis. `Decision` menunggu model `Shelf` di `dev`.
- CRUD preferensi: tambah, ubah arah dan bobot, hapus. Pilihan nutrien dibatasi ke protein, serat, gula, natrium, lemak jenuh, dan energi.
- Pratinjau jumlah produk yang lolos saat preferensi disunting, lewat AJAX di `static/js/preferences.js`. Query memakai kolom gizi di `Product`.
- CRUD riwayat keputusan: catat produk terpilih dari sebuah shelf beserta alasan, baca riwayat pribadi, ubah, hapus. Tombol "Pilih produk ini" di tabel pembanding disiapkan bersama Daffaa (cukup satu form kecil).
- Seluruh isi modul ini hanya untuk pemiliknya. Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.
- Tes di `preferences/tests.py`: arah dan bobot, unik per nutrien, dan riwayat pribadi tidak bisa dibaca orang lain.
- Bonus: `preferences/ranking.py`, fungsi yang menerima daftar produk dan preferensi pengguna lalu mengembalikan urutan baris, dengan produk bernilai `"unknown"` tidak ikut diperingkat.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Modul 2 dan Modul 5 belum mulai | Model `Shelf` masuk `dev` lebih dulu supaya Jonathan tidak menunggu. Tujuh Aturan Khusus dulu, bonus belakangan |
| Modul 3 dan 4 cukup besar dan belum pernah digabung dengan modul lain | PR ke `dev` secepatnya, supaya konflik dan tes yang gagal ketahuan sejak awal |
| Modul 1 dan seeding belum pernah dicoba di PostgreSQL PWS | Dorong `dev` ke `main` lebih awal, lalu cek log deploy dan halaman katalog |
| Konflik di `settings.py`, `urls.py`, `base.html`, dan `pilihyuk/views.py` | Satu baris per app dan merge cepat. Perubahan di `base.html` hanya lewat Daffaa |
| Tailwind CDN gagal dimuat (tanpa internet) lalu tampilan rusak | Pastikan koneksi internet saat demo dan uji di PWS |
| Anggota lupa menambah `SECRET_KEY` ke `.env` setelah pull | `manage.py` berhenti dengan `KeyError: 'SECRET_KEY'`. Cara mengisinya ada di README |
| Akun dikunci pihak iseng (lockout per email, termasuk admin) | Pengguna atau kurator tidak bisa masuk selama 15 menit. Diterima. Pulihkan dengan `python manage.py axes_reset`. Untuk demo kurator di PWS, siapkan akun dan jangan dites berlebihan sebelum demo |
| `Procfile` release belum teruji di PWS | Kalau gagal, tabel tidak terbentuk dan halaman error. Cek log deploy pertama; cadangannya `migrate` manual di PWS |
| Batas Open Food Facts 15 permintaan per menit per alamat | Lookup runtime dibatasi 3 per menit per pengguna. Seeding tidak memanggil API |
| Satu orang tidak sempat | Katakan lebih awal di grup. Yang paling mudah dialihkan: tes, responsif ponsel, dan bonus |
