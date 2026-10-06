# Timeline PilihYuk

Tenggat: Jumat, 23 Oktober 2026, 23.59 WIB. Dokumen ini untuk kelompok dan ikut di-commit di folder `.claude/`.

## Titik awal

Repo sudah punya scaffold Django, `base.html` dengan header dan footer, halaman landing dari data contoh, Tailwind, dan enam app yang sudah didaftarkan beserta folder `templates/<app>/` dan `static/js/<app>.js` yang masih kosong. Belum ada model produk, shelf, dan seeding. Wireframe Figma desktop sudah lengkap, frame ponsel belum.

**Pembaruan 4 Okt: auth (`accounts`) sudah selesai** dikerjakan Daffaa di `dev` (daftar, masuk, keluar, profil, 34 tes), lebih awal dari target Selasa 6 Okt. Sudah di `origin/dev` (belum di `main`), jadi setelah `git pull` di `dev` modul lain bisa menguji fitur yang butuh login lewat halaman Daftar.

Hampir semua modul membaca tabel `Product`, jadi `Product` harus masuk `dev` paling dulu.

## Hari pengerjaan

Hari pengerjaan proyek:

| Fase | Hari |
|------|------|
| Persiapan | Minggu 4 Okt (rapat dan setup) |
| 1. Fondasi | Selasa 6, Kamis 8 (malam), Sabtu 10 Okt |
| 2. Fitur inti | Jumat 16, Sabtu 17, Minggu 18 (pagi) Okt |
| 3. Penyelesaian | Selasa 20 sampai Jumat 23 Okt |

Totalnya sekitar tujuh hari kerja, jadi fitur dipilah menjadi wajib dan bonus.

## Pembagian

| Modul | Pemilik | App Django | Model |
|-------|---------|------------|-------|
| 1. Katalog Produk | Yasmin | `product_catalog` | `Product`, `ProductView` |
| 2. Shelf dan Tabel Pembanding | Daffaa | `shelves` | `Shelf`, `ShelfItem`, `SavedShelf` |
| 3. Substitusi Komunitas | Rafael | `substitutions` | `Substitution`, `SubstitutionVote` |
| 4. Antrean Data | Rayyan | `data_correction` | `DataCorrection`, `DataCorrectionItem` |
| 5. Preferensi dan Riwayat Keputusan | Jonathan | `preferences` | `Preference`, `Decision` |
| Auth | Daffaa | `accounts` | memakai `User` bawaan Django |

Template tiap modul masuk `templates/<app>/`, JavaScript-nya ke `static/js/<app>.js`, dan semua halaman mewarisi `base.html`. View yang dipakai AJAX juga punya versi JSON, karena Flutter nanti memakainya.

## Aturan kerja

- Alur branch: tiap modul atau app punya branch sendiri (misalnya `shelves`, yang sudah ada), lalu digabung ke `dev` untuk diuji bersama (`manage.py check` dan `manage.py test`), lalu `dev` di-push ke `main`. Push ke `main` sekaligus deploy ke PWS lewat GitHub Actions, jadi `main` harus selalu bisa jalan.
- Pengecualian: auth (`accounts`) dikerjakan Daffaa langsung di `dev`, karena kecil, dikerjakan sekali, dan semua modul segera membutuhkannya. Yang di-push ke `dev` hanya commit yang lulus `check` dan `test`.
- Branch modul dibuat sendiri oleh pemiliknya, dengan nama sama seperti app (`product_catalog`, `substitutions`, `data_correction`, `preferences`; `shelves` sudah ada). Buat dari `dev` yang terbaru, saat mulai mengerjakan: `git switch dev`, `git pull`, `git switch -c <nama_app>`, lalu `git push -u origin <nama_app>`.
- Jangan menyunting file milik modul lain. Kalau perlu perubahan di sana, minta pemiliknya atau buka PR kecil terpisah.
- `settings.py` dan `urls.py` hanya diubah satu baris per app. Kalau bentrok saat merge, simpan kedua baris.
- Kerja sehari-hari: commit kecil dengan pesan jelas (misalnya `feat: add product list view`), ambil `dev` terbaru ke branch-mu (`git merge dev`) supaya konflik ketahuan di branch sendiri, jalankan `manage.py check` dan `manage.py test`, lalu gabungkan ke `dev` dan buka halaman modul lain untuk memastikan tidak ada yang rusak. Daffaa yang mendorong `dev` ke `main`.
- Commit atas nama sendiri, di modul sendiri. Penilaian individu melihat kontribusi per modul.
- Urutan ketergantungan: Rafael, Rayyan, dan Jonathan menunggu `Product` dari Yasmin, dan Jonathan juga menunggu `Shelf` dari Daffaa untuk `Decision`. Sebelum auth masuk `dev`, uji fitur login dengan akun dari `python manage.py createsuperuser`.
- Tailwind jalan lewat script CDN, jadi tidak ada langkah build.
- Di luar hari pengerjaan, jangan menggabungkan ke `main`, karena tidak ada yang sempat memperbaiki kalau PWS rusak.
- Di setiap akhir fase (Sabtu 10, Minggu 18, Rabu 21), setiap pemilik modul mencentang tujuh Aturan Khusus untuk modulnya: model, view CRUD, template, form, AJAX, pembatasan login, dan filter dari database.

## Wajib dulu, bonus belakangan

Waktunya sempit, jadi tiap modul menyelesaikan tujuh Aturan Khusus lebih dulu. Itu yang dinilai. Fitur berikut dikerjakan hanya kalau bagian wajib sudah beres, paling cepat di Fase 3:

- Urutan tabel pembanding mengikuti preferensi pengguna (`preferences/ranking.py` dipasang di tabel). Ini bonus yang paling diutamakan, karena disebut di README sebagai unsur kebaruan.
- Antrean kontribusi diurutkan dari produk yang paling sering ada di shelf.
- Skor lingkungan estimasi untuk produk yang skor resminya kosong.
- Refresh data satu produk dari Open Food Facts.
- Frame ponsel di Figma. Tampilan tetap harus responsif, tetapi bisa langsung dikerjakan dengan Tailwind tanpa menggambar dulu.

Daftar ini usulan dan disepakati di rapat Minggu.

## Persiapan (Sabtu 3 dan Minggu 4 Oktober)

### Sudah selesai

Daffaa sudah membagikan link repo, ERD, dan `.env.prod` ke grup, mengunggah ERD terbaru ke Google Drive yang ditautkan README, dan menjadwalkan diskusi hari Minggu.

### Minggu 4 Okt: rapat

Daffaa menjelaskan timeline ini lewat `first-brief.md`. Yang diputuskan: seeding, Tailwind, pemeriksaan ERD, siapa menguji gabungan di `dev`, pengaturan `DEBUG`, dan daftar wajib dan bonus di atas.

### Semua anggota, selesai hari Minggu

- `git pull`, buat virtualenv, `pip install -r requirements.txt`, taruh `.env`, lalu `python manage.py runserver`. Pastikan landing page terbuka.
- Buka halaman landing dengan internet menyala dan pastikan tampilannya benar (Tailwind lewat CDN, tanpa build).
- Baca bagian modul sendiri di README dan ERD.
- Setelah Daffaa mengabari bahwa auth sudah di `dev`: tambahkan baris `SECRET_KEY=<teks acak apa saja>` ke `.env` (tanpa itu `manage.py` berhenti dengan `KeyError`), lalu `git pull`, `pip install -r requirements.txt`, dan `python manage.py migrate`. Cara memakai `@login_required` dan `is_staff` ada di README, bagian "Autentikasi dan pengaturan lokal".
- Halaman `/profil/` menaut ke `/preferensi/`, `/riwayat/`, dan `/shelf/saya/`, dan kartunya menyala sendiri begitu URL itu ada. Kalau path di app kalian berbeda, kabari Daffaa.
- `LANGUAGE_CODE = 'id'` membuat desimal di template tampil berkoma ("7,5 g"). Float di dalam nilai CSS atau JS (`style="width: {{ x }}%"`) jadi rusak, jadi pakai bilangan bulat atau `{{ x|unlocalize }}` setelah `{% load l10n %}`.

## Fase 1: fondasi (Selasa 6 sampai Sabtu 10 Oktober)

Target Sabtu 10 Okt siang: semua model sudah di `dev`, fixture 20 produk bisa dimuat, dan login berjalan. Sabtu sore dipakai untuk mulai CRUD dasar.

| Hari | Yang dikerjakan |
|------|-----------------|
| Sel 6 | Yasmin menggabungkan `Product` dan `ProductView` ke `dev`. Auth sudah selesai Daffaa (4 Okt) dan ada di `origin/dev`. Yang lain menulis model di branch masing-masing |
| Kam 8, malam | Daffaa menggabungkan model `Shelf`. Model lain digabung kalau sudah siap |
| Sab 10 | Sisa model digabung pagi hari. Fixture 20 produk masuk. Siang sampai sore: CRUD dasar tiap modul |

### Yasmin (Modul 1, `product_catalog`)

- `product_catalog/models.py`: `Product` dan `ProductView` sesuai ERD. Gabungkan ke `dev` paling lambat Selasa 6 Okt, karena Rafael, Rayyan, dan Jonathan menunggu `Product`. Kalau sempat, model bisa ditulis sejak Minggu.
- Terima `open_food_facts.py` dan `tests.py` dari Daffaa (drafnya ada di `.claude/pilihyuk-docs/drafts/product_catalog/`), salin ke `product_catalog/`, jalankan `python manage.py test`, lalu commit di branch modulmu. Isinya sudah berisi lookup barcode (`fetch_product()`), `normalize_barcode()`, `is_sold_in_indonesia()`, `has_value()`, dan pembaca CSV untuk seeding.
- Fixture 20 produk di `product_catalog/fixtures/products.json`, paling lambat Sabtu 10 Okt.
- `product_catalog/management/commands/seed_products.py`: baca CSV, ambil produk Indonesia dengan minimal 4 dari 6 baris pembanding terisi, hitung `halal_labeled`. Boleh mundur ke Fase 2.
- `product_catalog/views.py` dan `templates/product_catalog/`: daftar produk berpaginasi dan halaman detail (skor, gizi, bahan, alergen, porsi, tautan "Lihat di Open Food Facts").

### Daffaa (Modul 2, `shelves`, dan auth, `accounts`)

- **Selesai 4 Okt.** App `accounts` lengkap dengan 34 tes: halaman Masuk, Daftar, Profil, dan halaman kunci akun, mengikuti frame 12 di Figma. Login memakai email, percobaan login dibatasi (django-axes), dan header berubah menurut status login. Rincian fiturnya ada di README, bagian modul Accounts. Dikerjakan langsung di `dev`.
- **Selesai 4 Okt.** Konfigurasi: `SECRET_KEY` dari environment tanpa fallback, `DEBUG` mengikuti `PRODUCTION` (butir e rapat), `django~=5.2.0`, dan `Procfile` yang menjalankan `collectstatic` dan `migrate` saat rilis. `SECRET_KEY` dan `PRODUCTION` sudah diisi di PWS.
- Sengaja ditunda: masuk dengan Google (tombolnya ada tapi nonaktif), verifikasi email, reset password, halaman Ketentuan Layanan, dan frame ponsel untuk auth.
- Setelah `dev` digabung ke `main`, baca log deploy pertama di PWS. `Procfile` dan auth di PostgreSQL belum pernah dicoba.
- `shelves/models.py`: `Shelf`, `ShelfItem`, `SavedShelf`, dengan batas 12 produk divalidasi di form. Gabungkan Kamis 8 Okt malam, karena `Decision` milik Jonathan membutuhkannya.
- `shelves/views.py` dan `templates/shelves/`: daftar shelf publik dan form buat shelf.

### Rafael (Modul 3, `substitutions`)

- `substitutions/models.py`: `Substitution` (from, to, reason, proposed_by; unik pada pasangan produk dan from tidak sama dengan to) dan `SubstitutionVote` (nilai +1 atau -1, unik per pengguna). Ditulis Selasa 6 Okt setelah `Product` ada, digabung paling lambat Sabtu 10 Okt pagi.
- `substitutions/forms.py` dan `views.py`: form usul substitusi dan daftar usulan, dengan data dari fixture.
- `templates/substitutions/`: kartu usulan dan form, mengikuti wireframe.

### Rayyan (Modul 4, `data_correction`)

- `data_correction/constants.py`: daftar field `Product` yang boleh dikoreksi: `product_name`, `brand`, `quantity`, `category`, `origin`, `nova_group`, dan delapan kolom gizi (energi, protein, lemak, lemak jenuh, karbohidrat, gula, serat, natrium). Kode, `added_by`, `source`, grade, tag, gambar, dan kolom turunan tidak boleh. Ini tidak butuh model, jadi bisa dikerjakan sebelum Selasa.
- `data_correction/models.py`: `DataCorrection` (product, submitted_by, reviewed_by, created_at, reviewed_at) dan `DataCorrectionItem` (field_name, old_value, proposed_value, status, review_note; unik pada correction dan field). Ditulis Selasa 6 Okt setelah `Product` ada, digabung paling lambat Sabtu 10 Okt pagi.
- `data_correction/forms.py` dan `views.py`: form pengajuan koreksi untuk satu produk dengan beberapa field.
- `templates/data_correction/`: halaman form dan daftar pengajuan milik pengguna.

### Jonathan (Modul 5, `preferences`)

- `preferences/models.py`: `Preference` (nutrient, direction, weight; unik per pengguna dan nutrien) dan `Decision` (user, shelf, product, note, created_at). `Preference` tidak butuh model lain, jadi bisa ditulis sejak Minggu. `Decision` menunggu model `Shelf` (Kamis 8 Okt malam), digabung paling lambat Sabtu 10 Okt pagi.
- `preferences/forms.py` dan `views.py`: daftar dan form preferensi. Pilihan nutrien dibatasi ke protein, serat, gula, natrium, lemak jenuh, dan energi.
- `templates/preferences/`: halaman preferensi dan halaman riwayat keputusan.

## Fase 2: fitur inti (Jumat 16 sampai Minggu 18 Oktober)

Target Minggu 18 Okt siang: semua modul sudah digabung dari `dev` ke `main` dan bisa didemokan bersama di PWS, dengan ketujuh Aturan Khusus terpenuhi.

| Hari | Yang dikerjakan |
|------|-----------------|
| Jum 16 | CRUD lengkap dan form tiap modul |
| Sab 17 | AJAX, filter dari database, dan pembatasan login. Malam: semua modul digabung ke `dev` dan diuji bersama |
| Min 18, pagi | Perbaiki yang rusak di `dev`, lalu `dev` didorong ke `main` dan dicek di PWS |

### Yasmin (`product_catalog`)

- Tambah produk lewat barcode (lookup Open Food Facts, tolak produk non-Indonesia dengan pesan yang menawarkan input manual) dan lewat form manual dengan bahan, alergen, dan porsi opsional. Batas 3 lookup per menit per pengguna dipasang di view ini.
- Sunting produk milik sendiri. Kurator (`is_staff`) bisa menyunting produk manual siapa pun.
- Hapus produk berupa soft delete lewat `is_active`. Tolak penghapusan produk yang masih dipakai shelf, usulan, atau pengajuan koreksi.
- Filter dari database: kategori, merek, asal, Nutri-Score, dan "berlabel halal". Pencarian dan filter lewat AJAX, dengan endpoint JSON di `product_catalog/views.py`.
- Riwayat produk yang dilihat lewat `ProductView`, hanya tampil untuk pengguna yang login.
- Seeding penuh 196 produk, kalau belum selesai di Fase 1.
- Landing page: isi `featured_shelf()` di `pilihyuk/views.py` dengan produk dari `Product`. Grade harus huruf kecil `a` sampai `e`, `unknown` jadi `None`, dan natrium dikali 1000 menjadi mg. Kunci datanya tercatat di komentar atas `SAMPLE_PRODUCTS`.

### Daffaa (`shelves`, `accounts`)

- CRUD shelf: nama, konteks toko, deskripsi, publik atau privat. Hanya pemilik yang bisa menyunting dan menghapus. Shelf privat hanya tampil bagi pemiliknya.
- Tambah dan keluarkan produk dari shelf lewat AJAX. Kandidat produk disaring dari `Product` dan hanya yang aktif.
- Tabel pembanding: pilih sampai 4 produk dari shelf, tampilkan Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama, penanda nilai terbaik, dan `"unknown"` apa adanya tanpa diperingkat. Template di `templates/shelves/compare.html`, urutan ulang lewat `static/js/shelves.js`.
- "Simpan ke Shelf Saya" (`SavedShelf`) dan halaman "Shelf Saya": shelf sendiri dan shelf publik orang lain yang disimpan. Identitas penyimpan tidak tampil.
- Auth: `@login_required` dengan pengalihan balik ke halaman asal sudah tersedia (`LOGIN_URL`, `?next=` divalidasi). Tinggal dipasang di view shelf. Hak kurator lewat `is_staff`.
- Landing page: isi `featured_shelves()` di `pilihyuk/views.py` dengan shelf publik terbaru, lalu ganti tautan `/katalog/` dan `/shelf/` di `templates/index.html` dengan `{% url %}`.
- Minggu 18 pagi: dorong `dev` ke `main` dan cek PWS.

### Rafael (`substitutions`)

- CRUD substitusi: usul X diganti Y dengan alasan, sunting alasan, tarik usulan sendiri. Usulan punya arah, jadi X ke Y tidak berlaku sebaliknya.
- Suara setuju dan tidak setuju lewat AJAX di `static/js/substitutions.js`. Satu pengguna satu suara per usulan, bisa diubah atau ditarik. Jumlah suara dihitung dengan `annotate`.
- Daftar usulan dengan persetujuan terbanyak di halaman detail produk, lewat `{% include %}` dari `templates/substitutions/`. Koordinasikan titik pemasangannya dengan Yasmin.
- Filter dari database: kandidat pengganti disaring menurut kategori dan skor dari `Product`.
- Dikunci login: identitas pengusul dan hak memberi suara. Pengunjung bisa membaca usulan tanpa melihat siapa pengusulnya.

### Rayyan (`data_correction`)

- Pengajuan koreksi: satu produk, beberapa field, nilai usulan divalidasi sesuai tipe kolom. Pengaju bisa menarik pengajuan yang belum ditinjau.
- Antrean kurator di `templates/data_correction/queue.html`: hanya `is_staff`, tinjauan per field (setujui atau tolak dengan catatan). Persetujuan menulis nilai ke `Product`.
- Antrean kontribusi: produk dengan data kosong, dideteksi dari `misc_tags` dan kolom gizi kosong. Urutan berdasarkan frekuensi di shelf termasuk bonus.
- Kirim dan tinjau lewat AJAX di `static/js/data_correction.js`.
- Dikunci login: identitas pengaju dan riwayat pengajuan.

### Jonathan (`preferences`)

- CRUD preferensi: tambah, ubah arah dan bobot, hapus. Satu pengguna satu preferensi per nutrien.
- Pratinjau jumlah produk yang lolos saat preferensi disunting, lewat AJAX di `static/js/preferences.js`. Query memakai kolom gizi di `Product`.
- CRUD riwayat keputusan: catat produk terpilih dari sebuah shelf beserta alasan, baca riwayat pribadi, ubah, hapus. Tombol "Pilih produk ini" di tabel pembanding disiapkan bersama Daffaa (cukup satu form kecil).
- Seluruh isi modul ini hanya untuk pemiliknya. Teks antarmuka tidak boleh terbaca sebagai saran kesehatan.

## Fase 3: penyelesaian (Selasa 20 sampai Jumat 23 Oktober)

| Hari | Yang dikerjakan |
|------|-----------------|
| Sel 20 | Integrasi antar modul dan bonus yang paling diutamakan, kalau bagian wajib sudah beres |
| Rab 21 | Responsif ponsel dan tes. Fitur dibekukan malam ini |
| Kam 22 | Uji penuh di PWS sebagai pengunjung, pengguna, dan kurator. Perbaiki bug |
| Jum 23 | Cadangan sampai siang. Kumpulkan sebelum 23.59, bukan di menit terakhir |

### Yasmin

- Tautan "Lihat di Open Food Facts" dan atribusi di halaman detail. Cek `templates/components/footer.html` memuat lisensi ODbL dan CC BY-SA.
- Uji pagination dan filter dengan semua data seeding, dan pastikan query tidak lambat (`select_related`).
- Responsif ponsel untuk `templates/product_catalog/`.
- Tes di `product_catalog/tests.py`: lookup barcode, `is_sold_in_indonesia()`, soft delete, dan filter.
- Bonus: refresh data satu produk dari Open Food Facts yang melewati field dengan `DataCorrectionItem` disetujui, dan skor lingkungan estimasi.

### Daffaa

- Tautkan nilai `"unknown"` di tabel pembanding ke formulir koreksi Rayyan.
- Pasang tombol "Pilih produk ini" yang menyimpan `Decision` lewat view Jonathan.
- Responsif ponsel untuk tabel pembanding (dua produk per layar, scroll horizontal). Template auth sudah dicek di lebar 390 px (tanpa overflow); tinggal dicek di ponsel sungguhan dan PWS.
- Deploy: pastikan migrasi dan seeding berjalan di PostgreSQL PWS, cek `collectstatic`, dan pastikan halaman tampil benar dengan Tailwind CDN. Kamis 22 Okt jalankan semua alur sebagai pengunjung, pengguna, dan kurator.
- Tes di `shelves/tests.py`: batas 12 produk, hak akses shelf, dan `SavedShelf`. Tes alur auth di `accounts/tests.py` sudah selesai (34 tes).
- Bonus: pasang urutan dari `preferences/ranking.py` ke tabel pembanding untuk pengguna yang login.

### Rafael

- Pasang daftar usulan di halaman detail produk bersama Yasmin, lalu uji dengan data seeding sungguhan.
- Responsif ponsel untuk `templates/substitutions/`.
- Tes di `substitutions/tests.py`: arah usulan, unik pasangan, satu suara per pengguna, dan akses pengunjung.
- Bantu Daffaa menguji alur di PWS pada Kamis 22 Okt.

### Rayyan

- Responsif ponsel untuk `templates/data_correction/`.
- Tes di `data_correction/tests.py`: validasi field, tinjauan per field, akses `is_staff`, dan penolakan pengguna biasa.
- Siapkan akun kurator (`createsuperuser`) untuk demo di PWS.
- Bonus: antrean diurutkan dari produk yang paling sering ada di shelf, dan persetujuan koreksi tidak tertimpa refresh.

### Jonathan

- Responsif ponsel untuk `templates/preferences/`.
- Tes di `preferences/tests.py`: arah dan bobot, unik per nutrien, dan riwayat pribadi tidak bisa dibaca orang lain.
- Cek ulang teks antarmuka supaya tidak terbaca sebagai rekomendasi kesehatan.
- Bonus: `preferences/ranking.py`, fungsi yang menerima daftar produk dan preferensi pengguna lalu mengembalikan urutan baris, dengan produk bernilai `"unknown"` tidak ikut diperingkat. Daffaa memasangnya di tabel pembanding.

## Risiko

| Risiko | Penanganan |
|--------|------------|
| Kuis, tugas lain, dan UTS memotong waktu | Hanya sekitar tujuh hari kerja efektif. Tujuh Aturan Khusus dikerjakan dulu, bonus belakangan |
| `Product` terlambat dan tiga orang menunggu | Yasmin menggabungkan model Selasa 6 Okt walau seeding belum selesai. Yang lain memakai fixture kecil |
| Fase 2 hanya tiga hari | Model dan CRUD dasar harus sudah ada Sabtu 10 Okt, supaya Jumat 16 tidak mulai dari nol |
| Seeding CSV 1,28 GB lambat atau gagal | Mulai dari fixture 20 produk. Seeding penuh dijalankan terpisah dan hasilnya diekspor jadi fixture |
| Konflik di `settings.py`, `urls.py`, dan `base.html` | Satu baris per app dan merge cepat. Perubahan di `base.html` hanya lewat Daffaa |
| Tailwind CDN gagal dimuat (tanpa internet) lalu tampilan rusak | Pastikan koneksi internet saat demo dan uji di PWS |
| Daffaa memegang auth, model Shelf, dan integrasi | Auth sudah selesai 4 Okt. Kalau model Shelf meleset, yang lain lanjut dengan pengguna dari halaman Daftar atau `createsuperuser` |
| Anggota lupa menambah `SECRET_KEY` ke `.env` setelah pull | `manage.py` berhenti dengan `KeyError: 'SECRET_KEY'`. Sengaja tanpa nilai bawaan, jadi Daffaa mengumumkannya di grup bersamaan dengan push auth, dan README menjelaskan caranya |
| Akun dikunci pihak iseng (lockout per email, termasuk admin) | Pengguna atau kurator tidak bisa masuk selama 15 menit. Diterima. Pulihkan dengan `python manage.py axes_reset`. Untuk demo kurator di PWS, siapkan akun dan jangan dites berlebihan sebelum demo |
| `Procfile` release belum teruji di PWS | Kalau gagal, tabel auth dan axes tidak terbentuk dan halaman Masuk dan Daftar error. Cek log deploy pertama; cadangannya `migrate` manual di PWS |
| Batas Open Food Facts 15 permintaan per menit per alamat | Lookup runtime dibatasi 3 per menit per pengguna. Seeding tidak memanggil API |
| Satu orang tidak sempat | Katakan lebih awal di grup. Yang paling mudah dialihkan: tes, responsif ponsel, dan bonus |
