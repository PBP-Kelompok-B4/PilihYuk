# Brief rapat Minggu, 4 Oktober 2026

Tujuan rapat ini satu: Selasa 6 Oktober semua orang bisa langsung menulis model di modulnya tanpa menunggu atau bertanya lagi. Selasa penting karena itu satu-satunya hari kosong minggu ini; Senin, Rabu, Kamis, dan Jumat penuh kuis dan tenggat tugas lain. Durasinya sekitar satu jam: keputusan yang masih terbuka (bagian 1), lalu catatan teknis (bagian 2).

Jadwal, pembagian modul, aturan Git, dan tugas per orang ada di `timeline.md`. Dokumen ini hanya memuat apa yang perlu diputuskan atau diingat.

## 1. Keputusan yang perlu diambil (20 menit)

Tiap butir punya usulan. Kalau tidak ada keberatan, usulan itu yang dipakai.

### a. Seeding data produk

Data produk berasal dari Open Food Facts. Dump CSV mereka (1,28 GB) memuat 8.186 produk yang dijual di Indonesia, tetapi hanya 196 yang datanya cukup untuk dibandingkan, yaitu minimal 4 dari 6 baris pembanding terisi. Hanya 196 produk itu yang masuk katalog. Usulannya dua tahap.

**Tahap 1: fixture 20 produk.** Fixture adalah file JSON berisi baris data yang bisa dimuat ke database dengan satu perintah. Bentuknya kira-kira begini:

```json
[
  {
    "model": "product_catalog.product",
    "pk": 1,
    "fields": {
      "code": "0089686010947",
      "product_name": "Indomie Mi Goreng Original",
      "brand": "Indomie",
      "nutrition_grade": "unknown",
      "sodium_100g": 0.9,
      "source": "off",
      "is_active": true
    }
  }
]
```

`model` berisi nama app dan nama model dalam huruf kecil, `pk` adalah primary key baris itu, dan `fields` berisi nilai tiap kolom.

Yasmin mengambil 20 dari ke-196 produk tadi, dipilih supaya semua modul punya bahan uji:

- 4 sampai 5 produk sejenis, misalnya mie instan goreng, untuk mencoba shelf dan tabel pembanding.
- Beberapa kategori berbeda, supaya filter katalog terlihat bekerja.
- 1 sampai 2 produk dengan nilai kosong (Nutri-Score `"unknown"` atau gizi yang tidak ada), untuk tampilan "Tidak diketahui" dan antrean koreksi Modul 4.
- Minimal 1 produk berlabel halal, untuk filter "berlabel halal".

Fixture didahulukan karena perintah seeding (baca CSV, petakan ke `Product`, simpan) belum ditulis dan butuh waktu, sedangkan fixture kecil bisa jadi dalam beberapa jam. Rafael, Rayyan, dan Jonathan jadi sudah punya data saat mulai CRUD Sabtu 10. Cukup satu orang yang mengunduh CSV 1,28 GB, dan selama `Product` masih bisa berubah di Fase 1, memperbarui 20 baris jauh lebih ringan daripada 196.

**Membuat dan memakai fixture.** Yasmin mengisi database lokalnya (lewat Django admin atau perintah seeding), lalu mengekspornya:

```
python manage.py dumpdata product_catalog.product --indent 2 > product_catalog/fixtures/products.json
```

File itu di-commit. Anggota lain cukup menjalankan:

```
python manage.py migrate
python manage.py loaddata products.json
```

`loaddata` mencari `products.json` di folder `fixtures/` setiap app, lalu menyimpan semua barisnya dalam satu transaksi: kalau satu baris gagal, tidak ada yang tersimpan. Baris dicocokkan per `pk`, jadi baris baru ditambahkan, baris yang sudah ada ditimpa, dan baris lain dibiarkan. Perintah ini aman dijalankan berulang kali.

Yang perlu diperhatikan:

- `migrate` harus jalan dulu, karena tabelnya harus sudah ada.
- `loaddata` tidak memvalidasi isi. Ia melewati `save()` model dan validasi form, jadi data yang salah tetap tersimpan. Periksa fixture sebelum di-commit.
- Fixture ikut berubah bersama model. Kalau kolom `Product` diganti nama atau ada kolom wajib baru, ekspor ulang.
- Relasi ditulis dengan `pk`, misalnya `"added_by": null` untuk produk dari Open Food Facts yang tidak punya penambah.

**Tahap 2: seeding penuh 196 produk.** Perintah seeding dibuat di Fase 1 kalau sempat, paling lambat Fase 2 (16 sampai 18 Oktober), dan memuat ke-196 produk dari CSV. Fixture 20 produk tetap disimpan untuk tes dan pengembangan lokal.

Yang perlu disepakati: dua tahap ini, kriteria 20 produk, dan siapa yang mengunduh CSV.

### b. Tailwind CSS

Tailwind dipilih setelah melihat wireframe, karena desainnya memakai warna dan komponen sendiri: hijau merek, latar krem, kartu membulat. Gaya ditulis langsung sebagai class di template, misalnya `class="rounded-xl bg-mint px-5"`. Tailwind dimuat lewat script CDN, jadi tidak ada CLI atau langkah build, tetapi halaman butuh internet untuk tampil. Warna proyek dan komponen yang sering dipakai (`btn-brand`, `card`, `chip`) sudah ada di `templates/components/tailwind.html`.

Usulan: tetap Tailwind. Kalau ada yang lebih nyaman dengan Bootstrap, ini kesempatan terakhir untuk bilang, karena setelah template modul mulai ditulis, mengganti framework berarti menulis ulang semuanya.

### c. Pemeriksaan ERD

Tiap pemilik modul membuka ERD dan mengecek entitasnya:

- nama dan tipe kolom sudah sesuai kebutuhan halaman di wireframe
- kolom mana yang boleh kosong
- relasi ke entitas lain dan aturan hapusnya (`CASCADE`, `PROTECT`, atau `SET_NULL`)
- kombinasi kolom yang harus unik, misalnya satu pengguna hanya punya satu suara per usulan

Setelah migrasi pertama, mengubah kolom jadi repot karena data dan migrasi ikut berubah. Jadi koreksi sekarang, selagi masih di atas kertas.

### d. Siapa menguji gabungan di `dev`

Usulan: orang yang menggabungkan branch-nya ke `dev` sekaligus menjalankan aplikasi dan membuka halaman modul lain untuk memastikan tidak ada yang rusak. Daffaa yang mendorong `dev` ke `main`, supaya ada satu orang yang memastikan versi di PWS selalu jalan.

### e. Pengaturan `DEBUG`

Dulu `DEBUG` di `settings.py` mati untuk semua lingkungan, jadi error di laptop hanya menampilkan "Server Error (500)" tanpa penjelasan. Usulan: `DEBUG` menyala di laptop dan mati di PWS, mengikuti `PRODUCTION` di `.env`. Perubahan ini sudah dikerjakan Daffaa bersama auth.

### f. Wajib dulu, bonus belakangan

Dengan sekitar tujuh hari kerja, tidak semua fitur di README akan sempat. Usulan: tiap modul menyelesaikan tujuh Aturan Khusus lebih dulu, karena itu yang dinilai. Daftar bonus (urutan tabel mengikuti preferensi, antrean menurut frekuensi shelf, skor lingkungan estimasi, refresh produk, frame ponsel di Figma) ada di `timeline.md`, dikerjakan hanya kalau bagian wajib sudah beres, paling cepat Selasa 20.

Yang perlu disepakati: daftar itu, dan apakah ada fitur lain yang ingin dipindah ke bonus.

### g. Kapasitas

Jadwal sudah memperhitungkan kuis, tugas, dan UTS yang sama untuk semua anggota. Kalau ada yang punya kegiatan lain di hari kerja, misalnya kepanitiaan, sampaikan sekarang supaya tugasnya digeser sejak awal.

## 2. Catatan teknis untuk semua modul

- Hanya produk yang dijual di Indonesia yang masuk katalog. Dicek lewat `countries_tags`, bukan negara asal produk.
- Open Food Facts tidak memakai `null` untuk data kosong. Nilai kosong ditulis `"unknown"` atau `"not-applicable"`. Tampilkan sebagai "Tidak diketahui" dan jangan ikutkan dalam peringkat.
- Lookup barcode ke Open Food Facts dibatasi 3 kali per menit per pengguna. Semua pengguna berbagi satu alamat server, sedangkan Open Food Facts hanya mengizinkan 15 permintaan per menit per alamat.
- Atribusi ke Open Food Facts wajib ada di footer (sudah ada), dan halaman detail produk menautkan ke halaman produknya di Open Food Facts.
- Teks di modul preferensi tidak boleh terbaca sebagai saran kesehatan. Aplikasi hanya menyaring dan mengurutkan.
