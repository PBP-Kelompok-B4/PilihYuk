# PilihYuk

> Bandingkan gizi dan jejak lingkungan sebelum pilih satu.

Proyek Tengah Semester, Pemrograman Berbasis Platform (CSGE602022), Fakultas Ilmu Komputer, Universitas Indonesia, Semester Gasal 2026/2027. Kelompok 4, Kelas B, sub-tema Sustainable Food & Diet.

- Deployment PWS: https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/
- Desain Figma: https://www.figma.com/design/6CwhelVNc1lJ9XWB4OnYlc/Wireframe?m=auto&t=CVl65mv1cAQ71x4E-6
- ERD: https://drive.google.com/file/d/1ifEXnbhhhzuR_gfXwdXOaAetRQwDuM4c/view?usp=sharing
- Dokumen kerja tim: folder [`.ai/`](.ai/README.md)

## Deskripsi

PilihYuk menaruh gizi dan dampak lingkungan produk makanan dan minuman dalam satu tabel, supaya pengguna bisa memilih satu di antaranya.

Unit kerjanya adalah shelf: kumpulan produk yang saling menggantikan karena pengguna hanya akan mengambil satu. "Mie instan goreng di Alfamart" adalah shelf, dan "yang bisa dituang ke kopi" juga, walau isinya (susu UHT, susu bubuk, krimer, oat milk) lintas kategori. Pengguna membuat shelf, memakainya lagi, dan halaman shelf langsung berupa tabel pembanding.

## Latar Belakang

Orang memutuskan beli makanan kemasan dalam hitungan detik di depan rak. Klaim label seperti "alami" atau "rendah gula" tidak terstandar, jadi sulit dibandingkan antarmerek.

[Open Food Facts](https://world.openfoodfacts.org/) (OFF) punya data terstandar (Nutri-Score, NOVA, Green-Score), tetapi berbahasa Inggris dan disusun per kategori, padahal keputusan belanja sering melintasi kategori. Preferensinya hanya mengenal arah "hindari", dan data produk Indonesia masih jarang: dari 8.186 produk Indonesia di dump, Nutri-Score baru terisi di 5,3% dan skor lingkungan di 4,2%.

PilihYuk membawa data ini ke saat orang berbelanja, dalam bahasa Indonesia dan bentuk yang langsung bisa dibandingkan.

## Anggota Kelompok

| No | Nama | NPM | Modul |
|----|------|-----|-------|
| 1 | Yasmin | 2506606124 | Katalog Produk |
| 2 | Ahmad Rizki Daffaa | 2506543640 | Shelf dan Tabel Pembanding |
| 3 | Rafael Arlen Wijanarko | 2506613514 | Rekomendasi Komunitas |
| 4 | Muhammad Rayyan Basalamah | 2406496372 | Antrean Data |
| 5 | Jonathan Sebastian Sindhu | 2506619650 | Preferensi Nutrisi dan Riwayat Keputusan |

## Jenis Pengguna

| Jenis | Yang bisa dilakukan |
|-------|---------------------|
| Pengunjung | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, dan membaca rekomendasi tanpa melihat pembuatnya |
| Pengguna terdaftar | Semua di atas, ditambah mengelola shelf, membuat rekomendasi dan memberi suara, mengajukan koreksi data, mengatur preferensi nutrisi, dan mencatat keputusan |
| Kurator data / admin | Meninjau pengajuan koreksi (setujui atau tolak) dan menyunting produk manual |

Target utamanya mahasiswa dan pekerja muda di kota besar yang rutin belanja di minimarket. Ini asumsi kelompok dan belum diuji lewat wawancara.

## Unsur Kebaruan

OFF sudah punya perbandingan berdampingan dan preferensi berbobot, jadi dua hal itu bukan klaim kami. Yang kami ubah:

1. Shelf menggantikan kategori. Produk disusun menurut situasi saat memilih, dan shelf adalah entitas yang dikurasi pengguna.
2. Preferensi nutrisi dua arah. Nutrien, arah, dan bobot dipisah, sehingga pengguna bisa meminta "maksimalkan protein" selain "hindari gula". Urutan tabel mengikuti preferensi ini.
3. Rekomendasi lintas shelf. Pengguna menyarankan X diganti Y beserta alasannya, lalu pengguna lain setuju atau tidak setuju.
4. Antrean kelengkapan data. Produk yang datanya kosong muncul sebagai antrean kontribusi, diurutkan dari yang paling sering ada di shelf.
5. Skor estimasi yang transparan. Bila skor lingkungan resmi kosong, estimasi dihitung dari tingkat pemrosesan, kemasan, minyak sawit, dan asal produk, dan ditandai berbeda dari nilai resmi.

## Public API

Kami memakai API OFF (gratis, tanpa key untuk baca). Satu produk dibaca lewat barcode dengan v3. Pencarian memakai `/api/v2/search` karena belum ada di v3.

| Keperluan | Tautan |
|-----------|--------|
| Panduan API | https://openfoodfacts.github.io/openfoodfacts-server/api/ |
| Referensi OpenAPI v3 | https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/ref-v3 |
| Produksi | https://id.openfoodfacts.org/ |
| Dump data untuk seeding | https://world.openfoodfacts.org/data |
| Keterangan field | https://static.openfoodfacts.org/data/data-fields.txt |

- Aplikasi memanggil `id.openfoodfacts.org`. Subdomain ini menyaring pencarian ke produk Indonesia tetapi tidak menyaring baca barcode v3, jadi setiap produk diperiksa dengan `is_sold_in_indonesia()` sebelum masuk (seeding, lookup, dan refresh).
- Lookup barcode dibatasi 3 per menit per pengguna, karena semua pengguna berbagi satu alamat server dan OFF hanya mengizinkan 15 permintaan per menit per alamat.
- Skor lingkungan dibaca dari `environmental_score_grade`, dengan `ecoscore_grade` sebagai cadangan. Skor kosong disimpan sebagai `"unknown"` atau `"not-applicable"`, bukan `null`, dan tidak pernah diperingkat.
- Seeding awal memakai dump nightly OFF yang disaring ke produk Indonesia (406 produk ber-Nutri-Score). Saat aplikasi berjalan, API dipakai untuk mencari barcode baru dan menyegarkan satu produk.
- Filter dijalankan di database lokal, bukan di API. Atribusi ke OFF (ODbL) ada di footer dan halaman produk.

## Menjalankan Proyek

Buat `.env` (tidak di-commit):

```
PRODUCTION=False
SECRET_KEY=<teks acak apa saja>
```

`SECRET_KEY` tidak punya nilai bawaan. Buat nilainya dengan `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"`. `DEBUG` mengikuti `PRODUCTION`: PostgreSQL bila `PRODUCTION=True` (di PWS), SQLite bila tidak.

```
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_products
python manage.py runserver
python manage.py test
```

Hasil terakhir: `check` bersih, 525 tes lulus (7 tes browser di `preferences` dilewati tanpa Chrome), cakupan sekitar 93%. Tes Modul 1 ada di `tests.py` dan paket `test_suites/`, sedangkan mapping dan manifes seed OFF ada di paket `seed/`.

## Tampilan

Tailwind CSS v4 lewat script CDN (`@tailwindcss/browser`), tanpa CLI, Node.js, atau langkah build, jadi butuh internet. Tema dan kelas komponen (`btn-brand`, `btn-secondary`, `card`, `chip`, `back-link`, `nav-chip`, dan lainnya) ada di `templates/components/tailwind.html`, dimuat oleh `base.html`. Halaman mewarisi `base.html` (header dan footer sebagai komponen), JavaScript ada di `static/js/<app>.js`, dan view AJAX juga menjawab JSON. Permintaan JSON ke URL yang tidak ada dijawab `{"error": "Tidak ditemukan."}`.

## Autentikasi

App `accounts` mengurus daftar, masuk, keluar, profil, dan reset password (`/lupa-password/`). Pengguna memakai `User` bawaan Django: `username` berisi email huruf kecil, `first_name` nama tampilan, `is_staff` menandai kurator. Login menerima email atau username dan dikunci 15 menit setelah 5 kegagalan per isian (django-axes).

```python
from django.contrib.auth.decorators import login_required, user_passes_test

@login_required                                   # pengunjung dialihkan ke /masuk/?next=...
def my_view(request): ...

@user_passes_test(lambda u: u.is_staff)           # hanya kurator
def curator_view(request): ...
```

Di template pakai `{% if user.is_authenticated %}` dan `{% firstof user.first_name user.username %}`. Query data pengguna selalu lewat `request.user`, dan email (yang juga username) tidak ditampilkan ke pengguna lain. Waktu disimpan dalam UTC dan ditampilkan menurut zona waktu browser (cookie `tz`, `pilihyuk/middleware.py`). `LANGUAGE_CODE = 'id'` membuat desimal di template berkoma, jadi nilai CSS atau JS memakai bilangan bulat atau `{{ x|unlocalize }}`.

Belum ada verifikasi email, pendaftaran belum dibatasi, dan `SECURE_SSL_REDIRECT` menunggu uji di proxy PWS.

## Modul dan Pembagian Kerja

### 1. Katalog Produk (Yasmin) · `/katalog/`

- Entitas: `Product`, `ProductView`.
- CRUD: tambah produk lewat barcode atau manual; daftar berpaginasi dan detail (skor, gizi, kemasan, gambar); sunting dan hapus entri sendiri (soft delete, produk yang masih dipakai shelf, rekomendasi, atau koreksi tidak bisa dihapus). Produk OFF dikoreksi lewat modul 4.
- Filter database: kategori, merek, asal, Nutri-Score, dan "berlabel halal" (penanda dari `labels_tags`, bukan pernyataan halal).
- Khusus login: penambah entri dan riwayat produk yang dilihat (`/katalog/riwayat/`).
- AJAX: pencarian dan filter katalog.

### 2. Shelf dan Tabel Pembanding (Ahmad Rizki Daffaa) · `/shelf/`

- Entitas: `Shelf`, `ShelfItem`, `SavedShelf`.
- CRUD: buat, ubah, dan hapus shelf; daftar shelf publik dan tabel pembanding (maksimal 4 produk: Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama, nilai terbaik); tambah dan keluarkan produk; "Simpan ke Shelf Saya" (`/shelf/saya/`).
- Filter database: kandidat produk shelf dari tabel `Product`.
- Khusus login: membuat dan menyunting shelf, shelf privat, dan koleksi tersimpan.
- AJAX: tambah dan keluarkan produk, simpan shelf, dan pilih produk yang dibandingkan.
- Catatan: satu shelf paling banyak 12 produk. Nilai `"unknown"` ditampilkan apa adanya dan ditautkan ke modul 4. Bagi pengguna login, urutan baris mengikuti preferensi (modul 5) dan ada tombol "Pilih ini" yang mencatat keputusan.

### 3. Rekomendasi Komunitas (Rafael Arlen Wijanarko) · `/rekomendasi/`

- Entitas: `Recommendation`, `RecommendationVote`.
- CRUD: buat rekomendasi X diganti Y beserta alasan; daftar dan detail; sunting alasan; tarik rekomendasi sendiri.
- Filter database: daftar bisa dicari menurut nama produk dan diurutkan (terbaru atau skor tertinggi), berpaginasi 10 per halaman. Kandidat pengganti disaring menurut kategori yang sama.
- Khusus login: nama pembuat, hak memberi suara, sunting, dan tarik.
- AJAX: tombol setuju dan tidak setuju.
- Catatan: rekomendasi berarah (X ke Y tidak otomatis berlaku sebaliknya). Satu pengguna punya satu suara per rekomendasi, bisa diubah atau ditarik, dan pembuat tidak bisa memilih rekomendasinya sendiri.

### 4. Antrean Data (Muhammad Rayyan Basalamah) · `/antrean/`, `/moderasi/`

- Entitas: `DataCorrection`, `DataCorrectionItem` (satu pengajuan untuk satu produk, ditinjau per field).
- CRUD: ajukan koreksi; antrean produk yang paling butuh dilengkapi (diurutkan dari yang paling sering ada di shelf); pengajuan saya dan penarikan; kurator menyetujui atau menolak di `/moderasi/`.
- Filter database: produk dengan data belum lengkap (dari `misc_tags` dan kolom gizi yang kosong).
- Khusus login: identitas pengaju, riwayat pengajuan, dan halaman moderasi (kurator).
- AJAX: kirim dan tinjau pengajuan.
- Catatan: hanya untuk mengoreksi produk yang sudah ada, dan field yang boleh dikoreksi dibatasi daftar tetap.

### 5. Preferensi Nutrisi dan Riwayat Keputusan (Jonathan Sebastian Sindhu) · `/preferensi/`, `/keputusan/`

- Entitas: `Preference` (nutrien, arah, bobot) dan `Decision` (produk terpilih, shelf asal, alasan, tanggal).
- CRUD: tambah, ubah, dan hapus preferensi; catat, ubah, dan hapus keputusan (termasuk hapus massal dan ekspor CSV).
- Filter database: mencocokkan preferensi dengan kolom gizi `Product`, dan menyaring riwayat menurut kata kunci, shelf, dan tanggal.
- Khusus login: seluruh isi modul bersifat pribadi.
- AJAX: pratinjau jumlah produk yang lolos saat preferensi disunting, dan pemuatan riwayat.
- Catatan: nutrien dibatasi pada protein, serat, gula, natrium, lemak jenuh, dan energi. Aplikasi hanya menyaring dan mengurutkan, bukan memberi saran gizi.

## AI Disclosure

### Yasmin


### Ahmad Rizki Daffaa

Saya memakai Claude Code (model Claude Sonnet 5.5 dan Opus 5.5) untuk membantu menulis dan mengubah kode, menjalankan perintah, dan merapikan dokumen. Cakupannya Modul 2 (shelf dan tabel pembanding), autentikasi termasuk reset password, file bersama seperti `base.html`, komponen, dan Tailwind, riset API Open Food Facts, serta dokumentasi tim. Plugin ECC (security reviewer, Django reviewer, Playwright) saya pakai untuk meninjau kode dan mengecek tampilan di browser, dan Figma MCP untuk membaca wireframe supaya template mengikuti desain.

Sebelum AI menulis kode, saya memberinya konteks tertulis: aturan tugas, PRD, handoff, brief rapat, dan timeline. Acuannya saya tentukan sendiri (tutorial PBP 0 sampai 5, dokumentasi Tailwind, wireframe Figma, dan dokumentasi Open Food Facts). Untuk soal API, AI saya minta menguji langsung dan menyimpan responsnya, jadi kontraknya berasal dari bukti, bukan dugaan. Perubahan saya minta kecil dan mudah dibaca karena tim baru memakai Tailwind, dan tes serta tampilan di browser dicek sebelum commit. Semua commit dan push saya kerjakan sendiri, dan AI tidak boleh menjalankan Git.

Beberapa hasil AI salah atau tidak sesuai, dan saya perbaiki sendiri. AI menyimpulkan nama field skor lingkungan sudah berganti dan mengira subdomain `id.openfoodfacts.org` menyaring semua produk ke Indonesia. Keduanya terbukti keliru setelah diuji, sehingga kode membaca kedua nama field dan memakai `is_sold_in_indonesia()`. AI menamai app `catalog` dan `dataflags`, dan saya menggantinya menjadi `product_catalog` dan `data_correction`. Modul rak dan perbandingan saya gabung menjadi Modul 2. Panah ERD dan pilihan favicon butuh beberapa putaran sampai terbaca, dan dokumen buatan AI cenderung panjang sehingga beberapa kali saya minta dirapikan.

Tampilan paling banyak butuh arahan manual. Tombol setuju dan tidak setuju di rekomendasi awalnya tidak bergaya karena kelas `btn-secondary` belum pernah didefinisikan, dan tautan "Kembali", tombol, serta paginasi tampil berbeda di tiap halaman. Saya meminta AI menyeragamkannya dan memeriksa hasilnya di browser.

Pada 29 sampai 31 Oktober saya juga meminta AI menyunting sebagian modul anggota lain: larangan memilih usulan sendiri, filter, dan paginasi di Modul 3, perubahan rute riwayat keputusan menjadi `/keputusan/` di Modul 5, serta pemindahan kode seed dan tes Modul 1 ke folder `seed/` dan `test_suites/`. Pemilik modulnya perlu memeriksa perubahan itu.

Secara keseluruhan AI sangat membantu untuk backend, tes, dan dokumentasi. Klaim yang belum diuji dan tampilan sering salah atau kurang, jadi keduanya tetap saya periksa sendiri. Deployment di PWS, PostgreSQL, proxy, dan tampilan di ponsel sungguhan tidak bisa dicek AI, dan saya catat sebagai butir terbuka. Rekaman sesi tersedia kalau diminta.

### Rafael Arlen Wijanarko


### Muhammad Rayyan Basalamah


### Jonathan Sebastian Sindhu