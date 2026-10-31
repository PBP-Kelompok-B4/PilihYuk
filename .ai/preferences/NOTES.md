# Modul 5: Preferensi Nutrisi dan Riwayat Keputusan

Pemilik: Jonathan Sebastian Sindhu. Acuan tim: [PRD](../PRD.md), [HANDOFF](../HANDOFF.md), [timeline](../timeline.md), [README proyek](../../README.md).

Tailwind v4 dari CDN `@tailwindcss/browser` (tema di `templates/components/tailwind.html`), tanpa build, jadi demo butuh internet.

## Preferensi: draft dan simpan global

- Enam baris berurutan: Protein, Serat, Gula, Natrium, Lemak jenuh, Kalori (key `energy`, kolom `Product.energy_kcal_100g`). Bobot Rendah, Sedang, Tinggi = 1, 2, 3 (default 2). Arah awal: Protein dan Serat `max`, sisanya `min`. Baris `Preference` berarti aktif, tidak ada field status.
- Switch, arah, dan bobot hanya mengubah draft di memori halaman, tanpa autosave dan tanpa localStorage. Ringkasan dan pratinjau mengikuti draft, dan status menandai perubahan yang belum disimpan.
- "Simpan Preferensi" mengirim keenam baris dalam satu request. Backend memvalidasi semuanya sebelum transaksi, lalu membuat atau memperbarui baris aktif dan menghapus baris nonaktif milik `request.user` saja (baris pengguna dikunci selama transaksi). Bila gagal, draft tetap ada.
- "Reset" hanya mengosongkan draft (semua nonaktif, bobot 2, arah default). Database berubah setelah Simpan. Menyimpan semuanya nonaktif menghapus semua `Preference` pengguna dan tidak menyentuh `Decision`.

## Endpoint

| Metode | URL | Nama URL | Input |
|---|---|---|---|
| GET | `/preferensi/` | `preference_list` | Halaman draft |
| POST | `/preferensi/simpan/` | `preference_save` | JSON `preferences`, enam baris |
| POST | `/preferensi/pratinjau-gabungan/` | `preference_combined_preview` | JSON draft yang sama |
| GET | `/preferensi/pratinjau/` | `preference_preview` | Lama: `nutrient`, `direction` |
| POST | `/preferensi/tambah/` | `preference_create` | Lama: `nutrient`, `direction`, `weight` |
| POST | `/preferensi/<pk>/ubah/` | `preference_update` | Lama: `direction`, `weight` |
| POST | `/preferensi/<pk>/hapus/` | `preference_delete` | Lama: hapus satu baris |
| GET | `/keputusan/` | `decision_list` | `q`, `shelf`, `dari`, `sampai`, `bulan`, `page` |
| GET | `/keputusan/ekspor/` | `decision_export` | Filter yang sama, `page` diabaikan |
| POST | `/keputusan/tambah/` | `decision_create` | `product`, `shelf`, `note`, subset pembanding |
| POST | `/keputusan/<pk>/ubah/` | `decision_update` | `note` saja |
| POST | `/keputusan/<pk>/hapus/` | `decision_delete` | Hapus satu keputusan |
| POST | `/keputusan/hapus-massal/` | `decision_bulk_delete` | `ids` berulang. ID milik orang lain dan ID yang tidak ada sama-sama 404 |

Semua endpoint butuh login (pengunjung dialihkan ke Masuk dengan `?next=`), dan semua POST butuh CSRF, termasuk pratinjau gabungan yang hanya membaca. Endpoint lama menjawab JSON bila `Accept: application/json` atau `X-Requested-With: XMLHttpRequest`, selain itu HTML. API draft selalu JSON. Nama URL memakai namespace `preferences:`. Endpoint per baris dan pratinjau satu nutrien dipertahankan demi kompatibilitas, bukan untuk UI baru.

JSON draft (semua key wajib, nutrien tidak boleh ganda, `active` boolean, `weight` bilangan bulat 1 sampai 3):

```json
{"preferences": [
  {"nutrient": "protein", "active": true, "direction": "max", "weight": 3},
  {"nutrient": "fiber", "active": false, "direction": "max", "weight": 2},
  {"nutrient": "sugar", "active": true, "direction": "min", "weight": 2},
  {"nutrient": "sodium", "active": false, "direction": "min", "weight": 2},
  {"nutrient": "saturated_fat", "active": false, "direction": "min", "weight": 2},
  {"nutrient": "energy", "active": false, "direction": "min", "weight": 2}
]}
```

Respons:

- Simpan global: `{"ok": true, "message": "Preferensi disimpan.", "items": [...]}` (200). Item memuat `id`, `nutrient`, `nutrient_label`, `direction`, `weight`. CRUD per baris memakai `item` (201 untuk tambah, 200 untuk ubah dan hapus). Daftar: `{"ok": true, "items": [...]}`.
- Kesalahan: `{"ok": false, "message": "...", "errors": {"field": ["..."]}}` dengan status 400 (validasi), 403 (bukan pemilik), 404 (ID tidak ada), 405 (metode salah), atau 429 (rate limit). Middleware CSRF dan error server bisa menjawab HTML, dan fetch menanganinya tanpa menganggap penyimpanan berhasil.

## Pratinjau gabungan (F-5.7)

ORM mengambil `Product` aktif yang punya minimal satu nilai bukan NULL pada nutrien draft yang aktif, lalu `rank_products()` menghitung skor dan memilih paling banyak tiga. Tidak ada tulis `Preference` dan tidak ada panggilan OFF.

Respons: `ok`, `ranked_count`, `total_active`, `samples`, dan `state` (`inactive` bila tak ada preferensi aktif, `empty` bila tak ada kandidat berdata, `ready`). Sampel berisi `id`, `name`, dan `values` (label, value, unit). `None` tetap null, nol tetap 0, natrium dikali 1000 ke mg, satu desimal. Respons usang ditolak lewat nomor versi request.

Hitungannya disebut "produk dapat diperingkat", yaitu kandidat dengan minimal satu nilai relevan. F-5.7 menyebut "lolos" tanpa ambang angka, jadi implementasi mengurutkan dan tidak mengklaim ada filter ambang. Istilahnya masih perlu disepakati kelompok, dan angka 7 di desain hanya ilustrasi.

Skor: data parsial hanya menyumbang pada nutrien yang diketahui. Min-max dihitung antar kandidat per nutrien, arah `min` dibalik, lalu dijumlahkan dikali bobot. Bila semua nilai sama, kontribusinya 1 kali bobot. `None` bukan 0. Seri stabil menurut urutan `pk`.

## Kontrak Shelf: memilih produk dan subset pembanding

`POST /keputusan/tambah/` menerima `product` (wajib, aktif), `shelf` (opsional, harus terlihat dan memuat produk itu), `note` (opsional, maksimal 500), dan CSRF. Subset pembanding dikirim sebagai **field form berulang `compared_product_ids`**, bukan JSON atau angka:

```javascript
const body = new FormData();
body.set('product', selectedProductId);
body.set('shelf', shelfId);
body.set('note', note || '');
for (const id of comparedIds) body.append('compared_product_ids', String(id));
fetch('/keputusan/tambah/', {
  method: 'POST', body,
  headers: {'Accept': 'application/json', 'X-CSRFToken': csrfToken}
});
```

- `comparedIds` harus subset yang benar-benar dibandingkan di tabel (paling banyak 4), bukan seluruh isi shelf. JSON `/shelf/<pk>/?format=json` menyediakannya di `compared`, sedangkan `products` bisa berisi sampai 12 anggota.
- Bila subset dikirim: shelf wajib, 1 sampai 4 ID unik, semuanya produk aktif dan anggota shelf yang terlihat, dan subset memuat produk pilihan. Backend menghitung jumlah valid dalam transaksi yang sama dengan `Decision`, dan `compared_product_count` dari klien diabaikan. Tanpa subset, request lama tetap berhasil dengan count NULL, tanpa tebakan dan tanpa backfill.
- Tombol "Pilih ini" di tabel Shelf sudah memakai kontrak ini (28 Oktober). Formnya jalan tanpa JavaScript, dan dengan JavaScript hasilnya muncul sebagai toast.
- Respons tambah (201): `{"ok": true, "message": "Keputusan disimpan.", "item": {"id", "product_id", "product_name", "shelf_id", "shelf_name", "note", "created_at", "compared_product_count", ...}}`, ditambah `brand`, `quantity`, `image_url`, `product_url`, `shelf_url` untuk kartu.
- Relasi `product` dan `shelf` bersifat `SET_NULL`. Edit hanya mengubah `note`. Jumlah tetap setelah note, preferensi, isi shelf, atau relasi berubah. Validasi ID memastikan konteks sah saat pencatatan, dan bukan audit isi tabel yang pernah dilihat browser.

## Ranking untuk Shelf

`preferences/ranking.py` berisi dua fungsi murni: `rank_products(products, preferences)` untuk urutan produk, dan `order_metric_rows(preferences, default_rows)` yang menaikkan key nutrien preferensi aktif (bobot besar dahulu) dan membiarkan sisanya sesuai urutan bawaan.

```python
from preferences.ranking import order_metric_rows, rank_products

priorities = list(request.user.nutrition_preferences.all()) if request.user.is_authenticated else []
products = rank_products(products, priorities)
metric_keys = order_metric_rows(priorities, ["energy", "protein", "saturated_fat", "sugar", "fiber", "sodium"])
```

Baris tabel dibentuk oleh `shelves/comparison.py::comparison_rows(products, preferences)`, yang memetakan preferensi ke kolom lewat `NUTRIENT_FIELDS[...]["field"]`, jadi "Kalori" di sini cocok dengan "Energi" di tabel. Baris dengan preferensi aktif naik dan diberi `preferred: true`, dan urutan produk tidak berubah. Tanpa preferensi, arah bawaannya protein dan serat `max`, gula, natrium, dan lemak jenuh `min`, sedangkan energi, lemak, dan karbohidrat tidak diperingkat. Dengan preferensi aktif, nilai terbaik mengikuti arah preferensi, sehingga energi pun bisa diperingkat. Tes integrasinya ada di `shelves/tests.py` (`PreferenceIntegrationTests`).

## Riwayat keputusan

- Kartu menampilkan tanggal, produk dan shelf yang masih tersedia, gambar atau placeholder, alasan (di-escape), dan jumlah produk yang dibandingkan. Produk nonaktif atau FK NULL tetap mempertahankan `Decision` tetapi tampil "Tidak diketahui". Shelf yang kini privat milik orang lain disembunyikan dari HTML, JSON, CSV, dan chip.
- Tambah dan edit memakai dialog native (label, fokus awal, Escape, fokus kembali). Hapus tunggal dan massal meminta konfirmasi. Hapus massal menerima 1 sampai 100 ID, membuang duplikat, dan memeriksa seluruhnya dalam satu transaksi.
- Filter `q` (nama atau merek), `shelf`, `dari`, `sampai` (YYYY-MM-DD, inklusif, tanggal tak valid diabaikan dengan pemberitahuan), dan `bulan=ini`. Semuanya lewat ORM, sepuluh per halaman, dengan zona waktu proyek (UTC) dan URL diperbarui lewat `history.replaceState`.
- Ringkasan selalu seluruh riwayat pengguna (total keputusan, shelf unik yang masih terjangkau, produk unik dengan FK yang masih tercatat), tidak terpengaruh filter atau halaman.
- JSON riwayat memuat `ok`, `items`, `page`, `pages`, `total`, `notices`, `url`, `html`, ditambah `summary`, `tools_html`, `export_url`. CSV memakai filter yang sama tanpa paginasi (kolom `id`, `created_at`, `product_name`, `shelf_name`, `note`, `compared_product_count`), berawalan UTF-8 BOM, dan teks berawalan `= + - @` (termasuk setelah spasi atau karakter kontrol) diberi apostrof.
- State: loading dengan `aria-busy`, riwayat kosong berbeda dari filter kosong, "Bersihkan filter", error dengan "Coba lagi", submit ganda dicegah, dan respons usang tidak menimpa hasil baru. Penghapusan menyembunyikan baris sementara dan memulihkannya bila gagal.
- Rate limit tulis: 30 request per 60 detik per pengguna, termasuk simpan global. Pratinjau gabungan tidak memakai kuota. Respons 429 membawa `Retry-After: 60`. Cache bawaan `LocMemCache` bersifat per proses, jadi bukan kuota global antar-worker.

## Peta kode

- `constants.py`: pemetaan enam nutrien (label, satuan, skala), pilihan arah dan bobot, arah default, rate limit.
- `models.py`: `Preference` (unik per pengguna dan nutrien) dan `Decision` (`SET_NULL`, count nullable, `note` maksimal 500).
- `forms.py`: `PreferenceForm`, `PreferenceDraftForm` (enam baris sebelum tulis), `DecisionForm`, `DecisionFilterForm`, `DecisionBulkDeleteForm`.
- `views.py`: login, metode, dan pemilik dipasang sebelum logika. Simpan draft dan `Decision` memakai transaksi. `filtered_decisions()` menyatukan filter HTML, JSON, dan CSV, dan `decision_item()` menyensor metadata yang tidak boleh terlihat.
- `decorators.py`: deteksi JSON, pembatasan metode, pemilik (403 atau 404), dan limiter cache per pengguna. `ranking.py`: dua fungsi murni di atas. `urls.py`: namespace `preferences`.
- Migrasi: `0001_initial`, `0002_alter_decision_note` (validator 500), `0003_decision_compared_product_count` (nullable, tanpa backfill), `0004_alter_preference_nutrient` (label Kalori).
- Template di `templates/preferences/`: `preference_list.html`, `_preference_row.html`, `decision_list.html`, `_history_tools.html`, `_decision_results.html`, `_decision_row.html`, `_decision_dialogs.html`, `_forbidden.html`, `_error.html`. JavaScript di `static/js/preferences.js` (nama produk dan nilai pratinjau ditulis lewat `textContent`).
- Tes di `preferences/tests/` (model, form, view, draft, riwayat, otorisasi, hardening, ranking) dan `test_functional.py` (Playwright dan Chrome, opsional).

## Menjalankan tes

```
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test preferences
```

Tes browser butuh `PILIHYUK_BROWSER_TESTS=1`, paket Playwright, dan Chrome lokal. Tanpa itu, tes dilewati. Tes browser memeriksa lebar 390, 768, 1024, 1440 px tanpa overflow dan tidak memanggil OFF. Hasil terakhir seluruh proyek ada di README. Proxy dan deployment PWS belum diuji dari sisi modul ini.

## Ikon nutrien

Setiap baris memakai SVG Lucide lokal (Protein beef, Serat wheat, Gula candy, Natrium droplets, Lemak jenuh droplet, Kalori flame), dipilih oleh `_nutrient_icon.html` dari `templates/preferences/icons/`. Ikon bersifat dekoratif (`aria-hidden`), nama nutrien tetap jadi label teks, dan tidak ada dependency atau request tambahan. Sumber dan lisensi: https://github.com/lucide-icons/lucide, `preferences/LUCIDE_LICENSE.txt`.

## Pengungkapan AI

Alat: Codex di VS Code, untuk implementasi Django dan JavaScript, tes, inspeksi hasil command dan browser, serta dokumentasi. Batas model, form, HTTP, dan browser ditetapkan pengguna, dan tes perilaku ditulis lebih dulu. Koreksi selama pengerjaan: validator untuk `TextField.max_length`, ID filter shelf yang ganda, fokus saat DOM diganti, autosave diganti draft global, dan kebocoran nama shelf yang berubah privat. Keterbatasan: jumlah subset mencatat konteks valid dari klien, bukan audit tabel historis, kuota cache per proses, dan pemeriksaan pemilik tetap diperlukan untuk demo.
