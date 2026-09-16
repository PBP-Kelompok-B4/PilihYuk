# PilihYuk

> Bandingkan gizi dan jejak lingkungan sebelum pilih satu.

Proyek Tengah Semester, Pemrograman Berbasis Platform (CSGE602022)
Fakultas Ilmu Komputer, Universitas Indonesia, Semester Gasal 2026/2027
Kelompok **4**, Kelas **B**, Sub-tema: **Sustainable Food & Diet**

Desain Figma: -
Deployment PWS: -

## Deskripsi

PilihYuk menampilkan perbedaan gizi dan dampak lingkungan beberapa produk makanan dan minuman dalam satu tabel, supaya orang bisa memilih satu di antaranya.

Unit kerja utamanya bukan produk, melainkan **shelf**: kumpulan produk yang saling menggantikan, di mana pengguna hanya akan mengambil satu. "Mie instan goreng di Alfamart" adalah shelf. "Yang bisa dituang ke kopi" juga satu shelf, berisi susu UHT, susu bubuk, krimer, dan oat milk, meski isinya dari empat kategori berbeda. Shelf dibuat pengguna dan dipakai ulang pengguna berikutnya, jadi pekerjaan membandingkan tidak diulang dari nol. Halaman shelf langsung menampilkan isinya sebagai tabel pembanding.

## Latar Belakang

Orang memutuskan membeli makanan kemasan dalam hitungan detik, di depan rak minimarket, di antara lima sampai sepuluh produk yang terlihat setara. Harga mirip, kemasan mirip, dan klaim di label seperti "alami" atau "rendah gula" tidak terstandar sehingga tidak bisa diadu antar merek.

Data yang terstandar sudah ada, salah satunya ialah [OpenFoodFacts](https://world.openfoodfacts.org/) yang memiliki Nutri-Score untuk kualitas gizi, NOVA untuk tingkat pemrosesan, Green-Score untuk dampak lingkungan. Tapi data tersebut berbahasa Inggris dan tidak dibuka orang saat berbelanja. Data itu juga disusun berdasarkan kategori, yang menjawab "produk ini jenis apa", padahal pembeli butuh jawaban atas "di antara yang ada di depan saya, mana yang sebaiknya saya ambil". Satu kategori bisa memuat ribuan produk yang tidak pernah dijual di toko yang sama, dan sebaliknya satu keputusan nyata sering melibatkan beberapa kategori sekaligus.

Dua kekurangan lain. Alat bantu yang ada hanya mengenal preferensi yang bersifat menghindari, seperti rendah gula dan rendah garam, dengan asumsi masalah gizi setiap orang berupa kelebihan. Orang yang mencari kandungan tertinggi, misalnya protein atau zat besi, tidak punya cara menyatakannya. Lalu cakupan data produk Indonesia belum lengkap, terutama skor lingkungan, sehingga aplikasi yang hanya menampilkan data resmi akan penuh kolom kosong.


Pilihan konsumsi harian adalah keputusan yang paling sering diambil orang terhadap sistem pangan, tapi hampir selalu diambil tanpa pembanding. PilihYuk memindahkan data keberlanjutan pangan dari basis data terbuka ke momen keputusan itu, dalam bahasa Indonesia dan bentuk yang bisa langsung diadu. Shelf dan usulan substitusi yang dibuat satu pengguna jadi rujukan pengguna lain, jadi manfaatnya bertambah seiring kontribusi.

## Anggota Kelompok

| No | Nama | NPM | Modul |
|----|------|-----|-------|
| 1 | Yasmin | 2506606124 | Katalog Produk |
| 2 | [Nama] | [NPM] | Shelf dan Tabel Pembanding |
| 3 | [Nama] | [NPM] | Substitusi Komunitas |
| 4 | Rayyan | 2406496372 | Antrean Data |
| 5 | [Nama] | [NPM] | Preferensi Nutrisi dan Riwayat Keputusan |

## Jenis Pengguna

| Jenis | Yang Bisa Dilakukan |
|-------|---------------------|
| **Pengunjung** | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, membaca usulan substitusi tanpa identitas pengusul |
| **Pengguna Terdaftar** | Semua di atas, ditambah mengelola shelf, mengusulkan substitusi dan memberi suara, mengajukan koreksi data, mengatur preferensi nutrisi, dan mencatat riwayat keputusan |
| **Kurator Data / Admin** | Meninjau pengajuan koreksi, menyetujui atau menolaknya, dan menyunting entri produk hasil kontribusi manual |



**Target pengguna utama:** mahasiswa dan pekerja muda di kota besar yang berbelanja rutin di minimarket, sudah punya niat memilih lebih baik, tapi tidak punya informasi pembanding di depan rak. Mereka membeli produk yang sama berulang kali, jadi satu shelf yang sudah dikurasi berguna untuk banyak kali belanja. Profil ini masih asumsi kelompok, belum divalidasi lewat wawancara.

## Inspirasi dan Unsur Kebaruan
**[Open Food Facts](https://world.openfoodfacts.org)** jadi sumber data sekaligus rujukan utama. Rujukan tersebut sudah memiliki perbandingan produk berdampingan dan preferensi pribadi berbobot, jadi kedua hal itu tidak kami klaim sebagai kebaruan. Yang kami ambil basis data dan gagasan tabel pembandingnya, bagian yang kami perbarui ialah unit pembandingnya, arah preferensi, dan cara menangani data kosong.

Adapun fitur tambahan atau pembeda dari proyek ini sebagai berikut.

**1. Shelf sebagai unit pembanding, bukan kategori.** Platform lain menyusun produk menurut klasifikasi jenis pangan. PilihYuk menyusunnya menurut situasi memilih. Kelompok seperti "yang bisa dituang ke kopi" tidak bisa dinyatakan lewat sistem kategori mana pun karena isinya lintas kategori. Sejauh penelusuran kami, belum ada platform pembanding pangan yang menjadikan kumpulan pilihan sebagai entitas yang dikurasi pengguna.

**2. Preferensi nutrisi dua arah.** Alat bantu yang ada hanya punya kriteria "rendah X" karena bertumpu pada komponen rumus Nutri-Score. PilihYuk memisahkan nutrien, arah, dan bobot, jadi pengguna bisa meminta "maksimalkan protein", bukan cuma "hindari gula". Urutan tabel pembanding mengikuti preferensi itu, bukan satu skor tunggal.

**3. Substitusi lintas shelf dari komunitas.** Pengguna mengusulkan produk X bisa diganti Y beserta alasannya, lalu pengguna lain menyetujui atau menolak. Usulan boleh menyeberangi shelf, misalnya krimer ke susu UHT, sehingga menjangkau hal yang tidak bisa dinyatakan keanggotaan shelf. Aplikasi lain menghitung alternatif lewat algoritma; di sini usulannya datang dari orang yang berbelanja di pasar yang sama dan menyertakan alasan yang bisa dinilai.

**4. Antrean kelengkapan data pasar Indonesia.** Produk berdata kosong tidak disembunyikan, melainkan ditampilkan sebagai antrean kontribusi, diurutkan menurut seberapa sering produk itu muncul di shelf. Kekurangan data jadi pekerjaan yang bisa dikerjakan pengguna.

**5. Skor estimasi yang transparan.** Kalau skor lingkungan resmi kosong, aplikasi menghitung estimasi dari tingkat pemrosesan, jenis kemasan, kandungan minyak sawit, dan asal produk. Nilai estimasi selalu ditandai berbeda dari nilai resmi.

## Public API

**Open Food Facts API**, gratis dan tanpa API key untuk operasi baca. Pembacaan satu produk lewat barcode memakai v3 yang berstatus current, sedangkan pencarian terstruktur memakai `/api/v2/search` karena endpoint itu belum tersedia di v3 meski v2 sudah deprecated.

| Keperluan | Tautan |
|-----------|--------|
| Pengantar dan panduan API | https://openfoodfacts.github.io/openfoodfacts-server/api/ |
| Referensi OpenAPI v3 | https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/ref-v3 |
| Cheatsheet endpoint | https://openfoodfacts.github.io/openfoodfacts-server/api/ref-cheatsheet/ |
| Produksi | https://id.openfoodfacts.org/ |
| Staging (basic auth `off` / `off`) | https://world.openfoodfacts.net/ |
| Dump data untuk seeding | https://world.openfoodfacts.org/data |
| Keterangan field | https://static.openfoodfacts.org/data/data-fields.txt |

Pemanggilan runtime memakai subdomain negara `id.openfoodfacts.org` agar hasilnya sudah tersaring ke produk yang beredar di Indonesia. Dump untuk seeding tetap diambil dari `world`, karena ekspor hariannya global dan tidak tersedia per negara.

Field yang dipakai: `code`, `product_name`, `brands`, `quantity`, `image_url`, `nutrition_grades`, `nova_group`, `categories_tags`, `labels_tags`, `countries_tags`, `packaging_tags`, `ingredients_analysis_tags`, `nutriments`, `misc_tags`, dan skor lingkungan. Nama field skor lingkungan berbeda antar versi: v3 memakai `environmental_score_grade` mengikuti penggantian nama Eco-Score menjadi Green-Score, sedangkan v2 masih memakai `ecoscore_grade` dan mengabaikan nama baru itu bila diminta. Nilai yang tidak diketahui dikembalikan sebagai string `"unknown"`, bukan `null`.

Data masuk lewat dua jalur:
- **Seeding awal** memakai dump nightly Open Food Facts, bukan pemanggilan API berulang, karena di dokumentasi disarankan untuk mengunduh CSV atau JSONL untuk kebutuhan di atas beberapa ratus produk dan ada limit yang return HTTP 503. Dump disaring ke `countries_tags` Indonesia lalu diekspor jadi fixture Django. 
- **Pemanggilan runtime** dipakai untuk pencarian barcode produk yang belum ada di katalog dan penyegaran data satu produk, dengan header User-Agent yang mengidentifikasi aplikasi ini.

## Modul dan Pembagian Kerja
### 1. Katalog Produk - Yasmin

Pintu masuk aplikasi: penelusuran, halaman detail, dan penambahan produk lokal yang belum ada di Open Food Facts.

- **Entitas:** `Product`
- **CRUD:** pengguna menambah produk lewat barcode atau isian manual, membaca daftar berpaginasi dan halaman detail berisi skor, gizi per 100 g, kemasan, dan gambar, lalu menyunting atau menghapus entri buatannya sendiri
- **Filter API:** kategori, merek, negara asal, dan Nutri-Score, termasuk pada hasil pencarian barcode langsung ke API
- **Dikunci login:** identitas penambah entri dan riwayat produk yang pernah dilihat
- **AJAX:** pencarian dan pemfilteran katalog

### 2. Shelf dan Tabel Pembanding - [Nama anggota 2]

Modul inti. Shelf adalah kumpulan produk yang saling menggantikan, dan halamannya langsung berupa tabel pembanding.

- **Entitas:** `Shelf`, `ShelfItem`
- **CRUD:** membuat shelf dengan nama, konteks toko, dan deskripsi; membaca daftar shelf publik dan tabel pembanding berisi Nutri-Score, Green-Score, NOVA, kemasan, asal, dan gizi utama dengan penanda nilai terbaik per baris; menambah atau mengeluarkan produk; menghapus shelf sendiri
- **Filter API:** penyaringan kandidat produk yang boleh masuk shelf
- **Dikunci login:** pembuatan dan penyuntingan shelf, serta shelf privat
- **AJAX:** menambah, mengeluarkan, dan mengurutkan ulang isi tabel
- **Catatan:** isi shelf dibatasi dua belas produk agar tidak merosot jadi kategori. Nilai `"unknown"` ditampilkan apa adanya sebagai tidak diketahui, tidak ikut diperingkat, dan diberi tautan ke modul 4. Urutan baris mengikuti preferensi dari modul 5 kalau pengguna sudah login

### 3. Substitusi Komunitas - [Nama anggota 3]

Usulan penggantian produk beserta alasannya, dinilai pengguna lain, boleh menyeberangi shelf.

- **Entitas:** `Substitution`
- **CRUD:** mengusulkan X bisa diganti Y beserta alasan tertulis, membaca usulan yang paling banyak disetujui di halaman produk, menyunting alasan, dan menarik usulan sendiri
- **Filter API:** kandidat pengganti disaring menurut kategori dan skor
- **Dikunci login:** identitas pengusul, hak memberi suara, dan riwayat usulan
- **AJAX:** tombol setuju dan tidak setuju
- **Catatan:** substitusi punya arah. Usulan X ke Y tidak otomatis berlaku sebaliknya

### 4. Antrean Data - Rayyan

Jalur perbaikan data sekaligus antrean pekerjaan bagi kontributor.

- **Entitas:** `DataFlag`
- **CRUD:** mengajukan koreksi saat data produk keliru atau kosong, membaca antrean produk Indonesia yang paling butuh dilengkapi (diurutkan menurut frekuensi kemunculan di shelf), kurator menyetujui atau menolak, dan pengaju menarik pengajuannya
- **Filter API:** penyaringan produk lewat `misc_tags` untuk mendeteksi entri yang datanya belum lengkap
- **Dikunci login:** identitas pengaju dan riwayat pengajuan
- **AJAX:** pengiriman dan peninjauan pengajuan

### 5. Preferensi Nutrisi dan Riwayat Keputusan - [Nama anggota 5]

Menyimpan kebutuhan gizi pengguna beserta arahnya, lalu mencatat keputusan yang akhirnya diambil.

- **Entitas:** `Preference` (nutrien, arah, bobot) dan `Decision` (produk terpilih, shelf asal, alasan, tanggal)
- **CRUD:** menambah preferensi seperti maksimalkan protein atau minimalkan gula, mencatat keputusan setelah melihat tabel pembanding, membaca preferensi aktif dan riwayat pribadi, mengubah arah dan bobot, lalu menghapusnya
- **Filter API:** pencocokan preferensi dengan `nutriments`, `ingredients_analysis_tags`, dan `labels_tags`
- **Dikunci login:** seluruh isi modul ini pribadi
- **AJAX:** pratinjau jumlah produk yang lolos filter saat preferensi disunting
- **Catatan:** nutrien yang ditawarkan dibatasi pada yang datanya tersedia di Open Food Facts. Aplikasi menyaring dan mengurutkan produk, bukan memberi saran gizi, dan teks antarmuka menghindari kalimat yang terbaca sebagai rekomendasi kesehatan
