# PilihYuk

> Bandingkan gizi dan jejak lingkungan sebelum pilih satu.

Proyek Tengah Semester, Pemrograman Berbasis Platform (CSGE602022)
Fakultas Ilmu Komputer, Universitas Indonesia, Semester Gasal 2026/2027
Kelompok 4, Kelas B, Sub-tema: Sustainable Food & Diet

Deployment PWS: https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/

Desain Figma: https://www.figma.com/design/6CwhelVNc1lJ9XWB4OnYlc/Wireframe?m=auto&t=CVl65mv1cAQ71x4E-6

Database ERD: https://drive.google.com/file/d/1ifEXnbhhhzuR_gfXwdXOaAetRQwDuM4c/view?usp=sharing

## Deskripsi

PilihYuk menaruh gizi dan dampak lingkungan produk makanan dan minuman dalam satu tabel, supaya pengguna bisa memilih satu di antaranya.

Unit kerjanya adalah shelf, yaitu kumpulan produk yang saling menggantikan karena pengguna cuma akan mengambil satu. "Mie instan goreng di Alfamart" adalah shelf. "Yang bisa dituang ke kopi" juga shelf, walau isinya (susu UHT, susu bubuk, krimer, oat milk) berasal dari beberapa kategori. Pengguna membuat shelf dan memakainya lagi di lain waktu, dan halaman shelf langsung berupa tabel pembanding.

## Latar Belakang

Orang memutuskan beli makanan kemasan dalam hitungan detik di depan rak. Harga dan klaim label seperti "alami" atau "rendah gula" tidak terstandar, jadi sulit dibandingkan antar merek.

[Open Food Facts](https://world.openfoodfacts.org/) punya data yang sudah terstandar (Nutri-Score, NOVA, Green-Score), tapi berbahasa Inggris dan disusun per kategori, padahal keputusan belanja sering melintasi kategori. Preferensinya pun hanya mengenal arah "hindari": orang yang mencari kandungan tertinggi, misalnya protein, tidak bisa menyatakannya. Data produk Indonesia di sana juga masih jauh dari lengkap. Dari 8.186 produk Indonesia di dump, Nutri-Score baru terisi di 5,3% dan skor lingkungan di 4,2%.

PilihYuk membawa data ini ke saat orang berbelanja, dalam bahasa Indonesia dan bentuk yang langsung bisa dibandingkan. Shelf dan usulan substitusi yang dibuat satu pengguna bisa dipakai pengguna lain sebagai rujukan.

## Anggota Kelompok

| No | Nama | NPM | Modul |
|----|------|-----|-------|
| 1 | Yasmin | 2506606124 | Katalog Produk |
| 2 | Ahmad Rizki Daffaa | 2506543640 | Shelf dan Tabel Pembanding |
| 3 | Rafael Arlen Wijanarko | 2506613514 | Substitusi Komunitas |
| 4 | Muhammad Rayyan Basalamah | 2406496372 | Antrean Data |
| 5 | Jonathan Sebastian Sindhu | 2506619650 | Preferensi Nutrisi dan Riwayat Keputusan |

## Jenis Pengguna

| Jenis | Yang Bisa Dilakukan |
|-------|---------------------|
| Pengunjung | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, dan membaca usulan substitusi tanpa melihat siapa pengusulnya |
| Pengguna Terdaftar | Semua hal di atas, ditambah mengelola shelf, mengusulkan substitusi dan memberi suara, mengajukan koreksi data, mengatur preferensi nutrisi, dan mencatat riwayat keputusan |
| Kurator Data / Admin | Meninjau pengajuan koreksi lalu menyetujui atau menolaknya, dan menyunting produk yang ditambahkan secara manual |

Target pengguna utama kami adalah mahasiswa dan pekerja muda di kota besar yang rutin belanja di minimarket. Mereka ingin memilih dengan lebih baik, tapi tidak punya info pembanding di depan rak. Karena mereka sering membeli produk yang sama, shelf yang sudah dikurasi layak dipakai lagi. Ini masih asumsi kelompok dan belum kami uji lewat wawancara.

## Inspirasi dan Unsur Kebaruan

[Open Food Facts](https://world.openfoodfacts.org) adalah sumber data sekaligus rujukan kami. Mereka sudah punya perbandingan berdampingan dan preferensi berbobot, jadi dua hal itu tidak kami klaim sebagai kebaruan. Yang kami ubah adalah unit pembandingnya, arah preferensinya, dan cara menangani data kosong.

1. Shelf, bukan kategori. Produk disusun menurut situasi saat memilih, bukan menurut jenis pangan. "Yang bisa dituang ke kopi" tidak bisa dinyatakan lewat satu kategori pun karena isinya lintas kategori. Sejauh yang kami telusuri, belum ada platform pembanding pangan yang menjadikan kumpulan pilihan sebagai entitas yang dikurasi pengguna.

2. Preferensi nutrisi dua arah. Alat yang ada sekarang hanya punya kriteria "rendah X". Di PilihYuk, nutrien, arah, dan bobot dipisah, jadi pengguna bisa meminta "maksimalkan protein" selain "hindari gula". Urutan tabel pembanding mengikuti preferensi ini, bukan satu skor tunggal.

3. Substitusi lintas shelf. Pengguna mengusulkan produk X diganti Y beserta alasannya, lalu pengguna lain menyetujui atau menolak. Usulan boleh menyeberangi shelf, misalnya dari krimer ke susu UHT. Bedanya dengan alternatif hasil algoritma, usulan di sini datang dari sesama pembeli dan alasannya bisa dinilai.

4. Antrean kelengkapan data pasar Indonesia. Produk yang datanya kosong muncul sebagai antrean kontribusi, diurutkan dari yang paling sering ada di shelf.

5. Skor estimasi yang transparan. Kalau skor lingkungan resmi kosong, kami menghitung estimasi dari tingkat pemrosesan, kemasan, minyak sawit, dan asal produk. Estimasi itu ditandai berbeda dari nilai resmi.

## Public API

Kami memakai API Open Food Facts (OFF). API ini gratis dan tidak butuh key untuk operasi baca. Satu produk dibaca lewat barcode dengan v3. Pencarian memakai `/api/v2/search` karena belum ada di v3, meski v2 sudah deprecated.

| Keperluan | Tautan |
|-----------|--------|
| Panduan API | https://openfoodfacts.github.io/openfoodfacts-server/api/ |
| Referensi OpenAPI v3 | https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/ref-v3 |
| Cheatsheet endpoint | https://openfoodfacts.github.io/openfoodfacts-server/api/ref-cheatsheet/ |
| Produksi | https://id.openfoodfacts.org/ |
| Staging (basic auth `off` / `off`) | https://world.openfoodfacts.net/ |
| Dump data untuk seeding | https://world.openfoodfacts.org/data |
| Keterangan field | https://static.openfoodfacts.org/data/data-fields.txt |

Saat aplikasi berjalan, kami memanggil `id.openfoodfacts.org`. Subdomain ini menyaring pencarian ke produk Indonesia, tetapi tidak menyaring pembacaan barcode lewat v3. Karena itu setiap produk diperiksa dengan `is_sold_in_indonesia()` (berdasarkan `countries_tags`) sebelum masuk, baik saat seeding, lookup barcode, maupun refresh. Dump seeding tetap diambil dari `world` karena OFF hanya menyediakannya secara global. Lookup barcode saat aplikasi berjalan dibatasi 3 per menit per pengguna, sebab semua pengguna berbagi satu alamat server dan OFF hanya mengizinkan 15 permintaan per menit per alamat.

Field yang kami pakai: `code`, `product_name`, `brands`, `quantity`, `image_url`, `nutrition_grades`, `nova_group`, `categories_tags`, `labels_tags`, `countries_tags`, `origins_tags`, `manufacturing_places`, `packaging_tags`, `ingredients_analysis_tags`, `ingredients_text`, `allergens_tags`, `serving_size`, `nutriments`, `misc_tags`, dan skor lingkungan. Skor lingkungan dibaca dari `environmental_score_grade`, dengan `ecoscore_grade` sebagai cadangan karena v2 dan v3 masih memakai nama lama. Skor yang kosong dikembalikan sebagai `"unknown"` (atau `"not-applicable"`), bukan `null`.

Data masuk lewat dua jalur. Atribusi ke OFF (ODbL) dan tautan "Lihat di Open Food Facts" ada di footer dan halaman produk.

- Seeding awal: dump nightly OFF, bukan panggilan API berulang. Dokumentasi OFF meminta dump dipakai untuk lebih dari beberapa ratus produk. Dump disaring ke produk Indonesia lalu diekspor menjadi fixture Django.
- Saat aplikasi berjalan: API dipakai untuk mencari barcode yang belum ada di katalog dan menyegarkan satu produk, dengan User-Agent yang menyebut aplikasi ini. OFF menormalisasi barcode (UPC 12 digit menjadi 13 digit), jadi `code` disimpan dari respons API, bukan dari ketikan pengguna.

Setiap anggota memfilter data dari database lokal, bukan dari Public/mock API. API hanya mengisi database.

## Tailwind CSS

Tampilan memakai Tailwind CSS v4 lewat standalone CLI, jadi Node.js tidak diperlukan. Susunannya mengikuti [dokumentasi Tailwind CLI](https://tailwindcss.com/docs/installation/tailwind-cli):

| File | Fungsi |
|------|--------|
| `src/input.css` | Sumber Tailwind: warna tema, font, dan kelas komponen kami (`btn-brand`, `card`, `chip`, dan lainnya) |
| `static/css/output.css` | Hasil build yang dipakai `base.html`. Ikut di-commit karena PWS tidak menjalankan Tailwind |
| `tailwindcss.exe` | CLI-nya. Tidak di-commit, jadi tiap anggota mengunduh sendiri |

Unduh CLI dari [halaman rilis Tailwind](https://github.com/tailwindlabs/tailwindcss/releases/latest), lalu taruh di folder `PilihYuk/`.

Di Windows:

```
curl -L -o tailwindcss.exe https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-windows-x64.exe
```

Di macOS atau Linux, pilih berkas `tailwindcss-*` yang cocok di halaman yang sama. Setelah mengubah template atau `src/input.css`, build ulang:

```
./tailwindcss.exe -i ./src/input.css -o ./static/css/output.css --minify
```

Selama mengerjakan tampilan, pakai `--watch` (tanpa `--minify`) agar CSS dibuat ulang setiap file disimpan. Jalankan build `--minify` sekali lagi sebelum commit.

Yang perlu diingat:

- Tailwind hanya membuat class yang tertulis utuh di template. Class yang dirakit dari data, seperti `bg-nutri-{{ huruf }}`, tidak terdeteksi dan harus didaftarkan lewat `@source inline(...)` di `src/input.css`. Sekarang daftarnya hanya untuk lencana Nutri-Score B dan C.
- Warna baru ditambahkan di blok `@theme`. Nama `--color-brand` otomatis menjadi `bg-brand`, `text-brand`, dan `border-brand`.
- Kelas yang dipakai berulang, misalnya tombol atau kartu, ditulis sekali di `@layer components` dengan `@apply`.
- Jangan menyunting `output.css` langsung. Isinya ditimpa setiap build.

## Autentikasi dan pengaturan lokal

File `.env` (tidak di-commit) wajib berisi dua baris:

```
PRODUCTION=False
SECRET_KEY=<teks acak apa saja>
```

`SECRET_KEY` tidak punya nilai bawaan, jadi tanpa baris itu `manage.py` berhenti dengan `KeyError: 'SECRET_KEY'`. Buat nilainya dengan `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`. Di PWS, `SECRET_KEY` dan `PRODUCTION=True` diisi di environment variables proyek. `DEBUG` mengikuti `PRODUCTION`. Setelah `git pull`, jalankan `pip install -r requirements.txt` dan `python manage.py migrate` (django-axes menambah paket dan tabel).

App `accounts` mengurus daftar, masuk, keluar, dan profil. Pengguna memakai `User` bawaan Django: `username` berisi email huruf kecil, `first_name` berisi nama tampilan, dan `is_staff` menandai kurator. Cara memakainya di modul lain:

```python
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required                                   # pengunjung dialihkan ke /masuk/?next=...
def my_view(request): ...

@user_passes_test(lambda u: u.is_staff)           # hanya kurator
def curator_view(request): ...
```

Untuk class-based view, pakai `LoginRequiredMixin` dan `UserPassesTestMixin`. Di template: `{% if user.is_authenticated %}` dan `{% firstof user.first_name user.username %}` untuk nama. Query data milik pengguna selalu lewat `request.user`, jangan menerima id pengguna dari URL atau form. Halaman `/profil/` menaut ke `/preferensi/`, `/riwayat/`, dan `/shelf/saya/`; kartunya aktif sendiri saat URL itu ada, jadi pakai path itu atau kabari Daffaa bila berbeda.

Batasan yang diketahui: tidak ada verifikasi email dan reset password. Login dikunci 15 menit setelah 5 kegagalan per email (django-axes), dan pendaftaran belum dibatasi. `SECURE_SSL_REDIRECT` dan `SECURE_PROXY_SSL_HEADER` belum dipasang sampai diuji di PWS. Akun admin dari `createsuperuser` masuk dengan username-nya pada kolom "Email".

## Modul dan Pembagian Kerja

### 1. Katalog Produk (Yasmin)

*Pintu masuk aplikasi.*

- Entitas: `Product`, `ProductView`
- CRUD: tambah produk (lewat barcode atau manual); baca daftar berpaginasi dan halaman detail (skor, gizi, kemasan, gambar); sunting entri sendiri; hapus entri sendiri berupa soft delete, dan produk yang masih dipakai shelf, usulan, atau pengajuan koreksi tidak bisa dihapus. Kurator bisa menyunting entri manual siapa pun, sedangkan produk dari Open Food Facts dikoreksi lewat modul 4
- Filter database: kategori, merek, asal produk, Nutri-Score, dan "berlabel halal" (penanda dari `labels_tags`, bukan pernyataan halal), dijalankan pada data `Product` di database. Pencarian barcode ke API hanya mengisi katalog, dan filter tidak dijalankan di API
- Dikunci login: identitas penambah entri dan riwayat produk yang dilihat
- AJAX: pencarian dan filter katalog

### 2. Shelf dan Tabel Pembanding (Ahmad Rizki Daffaa)

*Modul inti: kumpulan produk yang saling menggantikan, ditampilkan sebagai tabel pembanding.*

- Entitas: `Shelf`, `ShelfItem`, `SavedShelf`
- Simpan shelf: pengguna terdaftar bisa menyimpan shelf sendiri atau shelf publik milik orang lain lewat tombol "Simpan ke Shelf Saya" (ikon penanda). Identitas penyimpan tidak ditampilkan. Halaman jelajah shelf publik punya tombol "Shelf Saya" yang menuju halaman koleksi, berisi shelf buatan pengguna dan shelf publik orang lain yang ia simpan
- CRUD: buat shelf (nama, konteks toko, deskripsi); baca daftar shelf publik dan tabel pembanding (maksimal empat produk sekali bandingkan, memuat Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama, dan penanda nilai terbaik); tambah dan keluarkan produk; hapus shelf sendiri
- Filter database: kandidat produk yang boleh masuk shelf, disaring dari tabel `Product`
- Dikunci login: membuat dan menyunting shelf, serta shelf privat
- AJAX: menambah dan mengeluarkan produk, mengurutkan ulang tabel
- Catatan: satu shelf berisi paling banyak dua belas produk supaya tidak berubah jadi kategori. Nilai `"unknown"` ditampilkan apa adanya, tidak ikut diperingkat, dan ditautkan ke modul 4. Kalau pengguna login, urutan baris mengikuti preferensi di modul 5

### 3. Substitusi Komunitas (Rafael Arlen Wijanarko)

*Usulan penggantian produk yang dinilai komunitas dan boleh melintasi shelf.*

- Entitas: `Substitution`, `SubstitutionVote`
- CRUD: usulkan X diganti Y beserta alasannya; baca usulan dengan persetujuan terbanyak di halaman produk; sunting alasan; tarik usulan sendiri
- Filter database: kandidat pengganti disaring menurut kategori dan skor dari tabel `Product`
- Dikunci login: identitas pengusul, hak memberi suara, dan riwayat usulan
- AJAX: tombol setuju dan tidak setuju
- Catatan: usulan punya arah, jadi usulan X ke Y tidak otomatis berlaku sebaliknya. Satu pengguna punya satu suara per usulan, dan suara itu bisa diubah atau ditarik

### 4. Antrean Data (Muhammad Rayyan Basalamah)

*Jalur perbaikan data sekaligus antrean kontribusi.*

- Entitas: `DataCorrection`, `DataCorrectionItem` (satu pengajuan untuk satu produk, boleh memuat beberapa field, dan ditinjau per field)
- CRUD: ajukan koreksi saat data keliru atau kosong; baca antrean produk yang paling butuh dilengkapi, diurutkan dari yang paling sering muncul di shelf; kurator menyetujui atau menolak; pengaju bisa menarik pengajuannya
- Filter database: mendeteksi `Product` yang datanya belum lengkap, dari `misc_tags` yang tersimpan dan dari kolom gizi yang kosong
- Dikunci login: identitas pengaju dan riwayat pengajuan
- AJAX: kirim dan tinjau pengajuan
- Catatan: modul ini hanya untuk mengoreksi produk yang sudah ada. Produk baru ditambahkan lewat modul 1. Field yang boleh dikoreksi dibatasi pada daftar tetap

### 5. Preferensi Nutrisi dan Riwayat Keputusan (Jonathan Sebastian Sindhu)

*Kebutuhan gizi pengguna dan keputusan akhir yang ia ambil.*

- Entitas: `Preference` (nutrien, arah, bobot) dan `Decision` (produk terpilih, shelf asal, alasan, tanggal)
- CRUD: tambah preferensi (misalnya maksimalkan protein) dan catat keputusan; baca preferensi aktif dan riwayat pribadi; ubah arah dan bobot; hapus
- Filter database: mencocokkan preferensi dengan kolom gizi di `Product`
- Dikunci login: seluruh isi modul ini bersifat pribadi
- AJAX: pratinjau jumlah produk yang lolos filter saat preferensi disunting
- Catatan: pilihan nutrien dibatasi pada protein, serat, gula, natrium, lemak jenuh, dan energi, karena hanya itu yang cukup terisi di Open Food Facts. Aplikasi hanya menyaring dan mengurutkan, bukan memberi saran gizi, jadi teks antarmuka menghindari kesan rekomendasi kesehatan
