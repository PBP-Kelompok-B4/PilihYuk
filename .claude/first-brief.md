# Hasil rapat 4 Oktober 2026

Arsip. Semua keputusan di bawah sudah tercatat di `PRD.md` bagian 13 dan sebagian sudah dijalankan.

- **Seeding:** mulai dari fixture kecil supaya modul lain bisa langsung mencoba CRUD, lalu seeding penuh. Hasil akhirnya 406 produk (keputusan 16, belum final).
- **Tailwind** lewat CDN, tanpa build (keputusan 28).
- **ERD** diperiksa tiap pemilik modul sebelum migrasi pertama: tipe kolom, kolom yang boleh kosong, aturan hapus, dan kombinasi unik.
- **Uji gabungan:** yang menggabungkan branch ke `dev` menjalankan aplikasi dan membuka halaman modul lain. Daffaa yang menggabungkan `dev` ke `main`.
- **`DEBUG`** menyala di laptop dan mati di PWS, mengikuti `PRODUCTION`.
- **Wajib dulu, bonus belakangan** (keputusan 37).

Catatan fixture yang masih berguna:

- `migrate` dulu, baru muat data.
- `loaddata` tidak menjalankan validasi form, jadi periksa fixture sebelum di-commit.
- `loaddata` menimpa baris dengan `pk` yang sama. Untuk database yang sudah berisi, pakai `python manage.py seed_products`, yang melewati barcode yang sudah ada.
