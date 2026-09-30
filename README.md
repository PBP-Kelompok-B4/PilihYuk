# PilihYuk

> Bandingkan gizi dan jejak lingkungan sebelum pilih satu.

Proyek Tengah Semester, Pemrograman Berbasis Platform (CSGE602022)
Fakultas Ilmu Komputer, Universitas Indonesia, Semester Gasal 2026/2027
Kelompok **4**, Kelas **B**, Sub-tema: **Sustainable Food & Diet**

Deployment PWS: https://ahmad-rizki53-pilihyuk.pws.cs.ui.ac.id/

Desain Figma: https://www.figma.com/design/6CwhelVNc1lJ9XWB4OnYlc/Wireframe?m=auto&t=CVl65mv1cAQ71x4E-6

## Deskripsi
 
PilihYuk membandingkan gizi dan dampak lingkungan produk makanan dan minuman dalam satu tabel, supaya pengguna bisa memilih satu di antaranya.
 
Unit kerjanya adalah **shelf**: kumpulan produk yang saling menggantikan, karena pengguna cuma akan ambil satu. "Mie instan goreng di Alfamart" itu shelf. "Yang bisa dituang ke kopi" juga shelf, walau isinya (susu UHT, susu bubuk, krimer, oat milk) lintas kategori. Shelf dibuat dan dipakai ulang pengguna; halamannya langsung jadi tabel pembanding.
 
## Latar Belakang
 
Orang memutuskan beli makanan kemasan dalam hitungan detik di depan rak. Harga dan klaim label seperti "alami" atau "rendah gula" tidak terstandar, sulit dibandingkan antar merek.
 
[Open Food Facts](https://world.openfoodfacts.org/) punya data terstandar (Nutri-Score, NOVA, Green-Score), tapi berbahasa Inggris, disusun per kategori padahal keputusan belanja sering lintas kategori, dan preferensinya cuma mengenal arah "hindari". Orang yang cari kandungan tertinggi, misalnya protein, tidak bisa menyatakannya. Cakupan data Indonesia pun belum lengkap, terutama skor lingkungan.
 
PilihYuk memindahkan data ini ke momen belanja, dalam bahasa Indonesia dan bentuk yang langsung bisa dibandingkan. Shelf dan usulan substitusi yang dibuat satu pengguna jadi rujukan pengguna lain.
 
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
| **Pengunjung** | Menelusuri katalog dan shelf publik, melihat tabel pembanding, memakai filter, membaca usulan substitusi tanpa identitas pengusul |
| **Pengguna Terdaftar** | Semua di atas, ditambah mengelola shelf, mengusulkan substitusi dan memberi suara, mengajukan koreksi data, mengatur preferensi nutrisi, dan mencatat riwayat keputusan |
| **Kurator Data / Admin** | Meninjau pengajuan koreksi, menyetujui atau menolaknya, dan menyunting entri produk hasil kontribusi manual |
 
**Target pengguna utama:** mahasiswa dan pekerja muda di kota besar yang belanja rutin di minimarket, ingin memilih lebih baik tapi tidak punya info pembanding di depan rak. Mereka beli produk sama berulang kali, jadi shelf yang sudah dikurasi berguna dipakai lagi. Masih asumsi kelompok, belum divalidasi lewat wawancara.
 
## Inspirasi dan Unsur Kebaruan
 
**[Open Food Facts](https://world.openfoodfacts.org)** jadi sumber data sekaligus rujukan. Mereka sudah punya perbandingan berdampingan dan preferensi berbobot, jadi keduanya tidak kami klaim sebagai kebaruan. Yang kami ubah: unit pembanding, arah preferensi, dan cara menangani data kosong.
 
**1. Shelf, bukan kategori.** Produk disusun menurut situasi memilih, bukan klasifikasi jenis pangan. "Yang bisa dituang ke kopi" tidak bisa dinyatakan lewat kategori mana pun karena lintas kategori. Sejauh penelusuran kami, belum ada platform pembanding pangan yang menjadikan kumpulan pilihan sebagai entitas yang dikurasi pengguna.
 
**2. Preferensi nutrisi dua arah.** Alat bantu yang ada cuma punya kriteria "rendah X". PilihYuk memisahkan nutrien, arah, dan bobot, jadi pengguna bisa minta "maksimalkan protein", bukan cuma "hindari gula". Urutan tabel pembanding ikut preferensi ini, bukan satu skor tunggal.
 
**3. Substitusi lintas shelf.** Pengguna usulkan produk X diganti Y beserta alasan, pengguna lain menyetujui atau menolak. Usulan boleh menyeberangi shelf, misalnya krimer ke susu UHT. Beda dari alternatif algoritmik: di sini usulan datang dari sesama pembeli, dengan alasan yang bisa dinilai.
 
**4. Antrean kelengkapan data pasar Indonesia.** Produk berdata kosong ditampilkan sebagai antrean kontribusi, diurutkan dari yang paling sering muncul di shelf.
 
**5. Skor estimasi transparan.** Kalau skor lingkungan resmi kosong, dihitung estimasi dari tingkat pemrosesan, kemasan, minyak sawit, dan asal produk, ditandai beda dari nilai resmi.
 
## Public API
 
**Open Food Facts API**, gratis, tanpa key untuk operasi baca. Baca satu produk lewat barcode pakai v3 (current); pencarian terstruktur pakai `/api/v2/search` karena belum tersedia di v3 meski v2 sudah deprecated.
 
| Keperluan | Tautan |
|-----------|--------|
| Pengantar dan panduan API | https://openfoodfacts.github.io/openfoodfacts-server/api/ |
| Referensi OpenAPI v3 | https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/ref-v3 |
| Cheatsheet endpoint | https://openfoodfacts.github.io/openfoodfacts-server/api/ref-cheatsheet/ |
| Produksi | https://id.openfoodfacts.org/ |
| Staging (basic auth `off` / `off`) | https://world.openfoodfacts.net/ |
| Dump data untuk seeding | https://world.openfoodfacts.org/data |
| Keterangan field | https://static.openfoodfacts.org/data/data-fields.txt |
 
Runtime pakai subdomain `id.openfoodfacts.org` biar hasil tersaring ke produk Indonesia. Dump seeding tetap dari `world`, karena ekspornya global dan tidak tersedia per negara.
 
Field yang dipakai: `code`, `product_name`, `brands`, `quantity`, `image_url`, `nutrition_grades`, `nova_group`, `categories_tags`, `labels_tags`, `countries_tags`, `packaging_tags`, `ingredients_analysis_tags`, `nutriments`, `misc_tags`, dan skor lingkungan (`environmental_score_grade` di v3, `ecoscore_grade` di v2). Nilai kosong dikembalikan sebagai string `"unknown"`, bukan `null`.
 
Data masuk lewat dua jalur:
- **Seeding awal**: dump nightly Open Food Facts, bukan API berulang. Dokumentasi minta unduh CSV/JSONL untuk kebutuhan di atas beberapa ratus produk, dan ada limit yang mengembalikan HTTP 503. Disaring ke `countries_tags` Indonesia, diekspor jadi fixture Django.
- **Runtime**: cari barcode produk yang belum ada di katalog, dan segarkan data satu produk. Pakai header User-Agent yang mengidentifikasi aplikasi ini.
## Modul dan Pembagian Kerja
 
### 1. Katalog Produk — Yasmin
 
*Pintu masuk aplikasi.*
 
- **Entitas:** `Product`
- **CRUD:** tambah produk (barcode/manual); baca daftar berpaginasi dan detail (skor, gizi, kemasan, gambar); sunting/hapus entri sendiri. Kurator bisa sunting entri siapa pun
- **Filter API:** kategori, merek, negara asal, Nutri-Score, termasuk pada hasil pencarian barcode langsung ke API
- **Dikunci login:** identitas penambah entri, riwayat produk yang dilihat
- **AJAX:** pencarian dan filter katalog
### 2. Shelf dan Tabel Pembanding — Ahmad Rizki Daffaa
 
*Modul inti: kumpulan produk yang saling menggantikan, ditampilkan sebagai tabel pembanding.*
 
- **Entitas:** `Shelf`, `ShelfItem`
- **CRUD:** buat shelf (nama, konteks toko, deskripsi); baca daftar shelf publik dan tabel pembanding (Nutri-Score, Green-Score, NOVA, kemasan, asal, gizi utama, penanda nilai terbaik); tambah/keluarkan produk; hapus shelf sendiri
- **Filter API:** kandidat produk yang boleh masuk shelf
- **Dikunci login:** buat dan sunting shelf, shelf privat
- **AJAX:** tambah/keluarkan produk, urutkan ulang tabel
- **Catatan:** isi shelf maks dua belas produk agar tidak merosot jadi kategori. `"unknown"` ditampilkan apa adanya, tidak ikut diperingkat, ditautkan ke modul 4. Urutan baris ikut preferensi modul 5 kalau login
### 3. Substitusi Komunitas — Rafael Arlen Wijanarko
 
*Usulan penggantian produk, dinilai komunitas, boleh lintas shelf.*
 
- **Entitas:** `Substitution`
- **CRUD:** usulkan X diganti Y beserta alasan; baca usulan terbanyak disetujui di halaman produk; sunting alasan; tarik usulan sendiri
- **Filter API:** kandidat pengganti disaring kategori dan skor
- **Dikunci login:** identitas pengusul, hak memberi suara, riwayat usulan
- **AJAX:** tombol setuju dan tidak setuju
- **Catatan:** punya arah: usulan X ke Y tidak otomatis berlaku sebaliknya
### 4. Antrean Data — Muhammad Rayyan Basalamah
 
*Jalur perbaikan data sekaligus antrean kontribusi.*
 
- **Entitas:** `DataFlag`
- **CRUD:** ajukan koreksi saat data keliru/kosong; baca antrean produk paling butuh dilengkapi, urut frekuensi kemunculan di shelf; kurator approve/reject; pengaju tarik pengajuan
- **Filter API:** `misc_tags` untuk deteksi entri yang datanya belum lengkap
- **Dikunci login:** identitas pengaju, riwayat pengajuan
- **AJAX:** kirim dan tinjau pengajuan
### 5. Preferensi Nutrisi dan Riwayat Keputusan — Jonathan Sebastian Sindhu
 
*Kebutuhan gizi pengguna dan keputusan akhir yang diambil.*
 
- **Entitas:** `Preference` (nutrien, arah, bobot), `Decision` (produk terpilih, shelf asal, alasan, tanggal)
- **CRUD:** tambah preferensi (misal maksimalkan protein) dan catat keputusan; baca preferensi aktif dan riwayat pribadi; ubah arah/bobot; hapus
- **Filter API:** cocokkan preferensi dengan `nutriments`, `ingredients_analysis_tags`, `labels_tags`
- **Dikunci login:** seluruh isi modul ini pribadi
- **AJAX:** pratinjau jumlah produk lolos filter saat preferensi disunting
- **Catatan:** nutrien dibatasi pada yang datanya tersedia di Open Food Facts. Aplikasi menyaring dan mengurutkan, bukan memberi saran gizi; teks antarmuka menghindari kesan rekomendasi kesehatan
