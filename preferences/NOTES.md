# Modul 5 — Preferensi Nutrisi dan Riwayat Keputusan

Pemilik: Jonathan Sebastian Sindhu. Catatan implementasi per 26 Oktober 2026.

## Acuan terbaru dan penyesuaian

- [PRD tim](../.claude/PRD.md), terutama F-5.1–F-5.9, relasi Decision, serta keputusan 20, 28, dan 29.
- [Handoff](../.claude/HANDOFF.md) dan [timeline](../.claude/timeline.md) untuk kontrak integrasi dengan Shelf.
- [README proyek](../README.md#tailwind-css) dan `templates/components/tailwind.html` untuk gaya bersama.

Tailwind v4 dijalankan oleh script CDN `@tailwindcss/browser` melalui `base.html`. Tema dan komponen berada di `templates/components/tailwind.html`. Tidak ada langkah build, binary CLI, atau `static/css/output.css` yang perlu dibuat/di-commit. Ini mengikuti keputusan 28 dan pengarahan terbaru pemilik modul, menggantikan instruksi build lama pada AGENTS.md. Koneksi internet diperlukan untuk memuat CDN saat demo. Modul ini hanya menggunakan class yang tersedia dan utility Tailwind; file tema bersama tidak diubah.

Status Modul 5 dalam handoff/timeline tertanggal 23–24 Oktober mendahului implementasi ini. Status aktual S1–S11 dicatat di sini dan pada penanda Git `feat/preferences-*`. Halaman Masuk saat ini menerima email atau username; reset password sudah tersedia di app accounts. Tidak ada implementasi auth baru di modul ini.

Kontrak khusus Modul 5 tetap memakai `ok`, `message`, `item`, dan `errors` agar pemanggil Daffaa tidak rusak. Bentuk ini berbeda dari usulan kontrak umum dalam dokumen evaluasi SDK yang lebih lama; penyatuan kontrak lintas app untuk Flutter perlu kesepakatan tim, bukan perubahan sepihak di sini.

## Ringkasan per slice

| Slice | Hasil | Penanda lokal |
|---|---|---|
| S1 | Model Preference/Decision, konstanta, validator, migrasi, admin | `feat/preferences-models` |
| S2 | Form dan CRUD preferensi HTML, enam baris pengaturan, login wajib | `feat/preferences-preference-crud` |
| S3 | Pemeriksaan pemilik, 403 ramah untuk HTML/JSON, 404 untuk data hilang | `feat/preferences-authorization` |
| S4 | CRUD AJAX dan pratinjau ORM; NULL dikecualikan, 0 dihitung, natrium dikonversi ke mg | `feat/preferences-preference-ajax` |
| S5 | CRUD keputusan; validasi produk aktif, shelf terlihat, keanggotaan produk | `feat/preferences-decision-crud` |
| S6 | Filter database, sepuluh catatan per halaman, AJAX dan URL yang bisa dibagikan | `feat/preferences-decision-ajax-filter` |
| S7 | Tampilan 390–1440 px, label dan fokus keyboard, kontrol nonaktif disabled | `feat/preferences-responsive` |
| S8 | Fungsi murni pengurutan metrik dan ranking produk berbobot | `feat/preferences-ranking` |
| S9 | Rate limit, hapus massal atomik, tampilan optimistik dengan rollback | `feat/preferences-hardening` |
| S10 | Cakupan models/forms/views di atas target 90%, regresi keamanan dan browser opsional | `feat/preferences-coverage` |
| S11 | Kontrak integrasi, peta demo, verifikasi, dan AI disclosure; memakai CDN tanpa build | `feat/preferences-docs` |

## URL, metode, dan JSON

Semua endpoint memerlukan sesi login. Pengunjung diarahkan ke Masuk dengan `?next=`. Semua POST memerlukan CSRF. Kirim `Accept: application/json` atau `X-Requested-With: XMLHttpRequest` untuk JSON; tanpa header tersebut view menyediakan halaman HTML atau redirect setelah sukses. Pratinjau selalu mengembalikan JSON setelah login.

| Metode | URL | Nama URL | Input utama |
|---|---|---|---|
| GET | `/preferensi/` | `preferences:preference_list` | — |
| POST | `/preferensi/tambah/` | `preferences:preference_create` | `nutrient`, `direction`, `weight` |
| POST | `/preferensi/<pk>/ubah/` | `preferences:preference_update` | `direction`, `weight` |
| POST | `/preferensi/<pk>/hapus/` | `preferences:preference_delete` | — |
| GET | `/preferensi/pratinjau/` | `preferences:preference_preview` | `nutrient`, `direction` |
| GET | `/riwayat/` | `preferences:decision_list` | `q`, `shelf`, `dari`, `sampai`, `page` |
| POST | `/riwayat/tambah/` | `preferences:decision_create` | `product`, `shelf` opsional, `note` opsional |
| POST | `/riwayat/<pk>/ubah/` | `preferences:decision_update` | `note` |
| POST | `/riwayat/<pk>/hapus/` | `preferences:decision_delete` | — |
| POST | `/riwayat/hapus-massal/` | `preferences:decision_bulk_delete` | field `ids` berulang, 1–100 ID |

Endpoint hapus massal disetujui pemilik modul dalam percakapan pengerjaan. URL CRUD lama tetap sama.

Contoh preferensi sukses (201 saat dibuat, 200 saat diubah/dihapus):

```json
{"ok": true, "message": "Preferensi disimpan.", "item": {"id": 1, "nutrient": "protein", "nutrient_label": "Protein", "direction": "max", "weight": 2}}
```

Respons mutasi preferensi juga membawa `html` berupa satu baris yang sudah dirender server untuk menggantikan elemen halaman. Daftar preferensi: `{"ok": true, "items": [...]}`. Keberadaan Preference menandakan aktif; tidak ada field status tambahan. Bobot 1/2/3 adalah Rendah/Sedang/Tinggi, default 2. Arah awal `max`; pilihan lain `min` ditampilkan sebagai “Batasi”. Nutrien tidak dapat diganti melalui endpoint ubah.

Kesalahan validasi (400), kepemilikan (403), data hilang (404), metode (405), dan rate limit (429) memakai kode HTTP yang sesuai:

```json
{"ok": false, "message": "Periksa kembali isian.", "errors": {"weight": ["Bobot harus 1 sampai 3."]}}
```

```json
{"ok": false, "message": "Kamu tidak punya akses ke data ini."}
```

Penolakan CSRF ditangani middleware Django dan bisa berupa HTML. JavaScript menangani respons yang bukan JSON serta sesi yang berakhir. Jangan mengandalkan badan JSON untuk penolakan sebelum view dijalankan.

Pratinjau mengembalikan `ok`, `ranked_count`, `total_active`, dan maksimal tiga `samples` berisi `name`, `value`, `unit`. Hanya Product aktif dengan nilai gizi bukan NULL yang dihitung/diurutkan. Nilai sampel dibulatkan satu desimal; natrium dikali 1000. Bobot tidak mengubah pratinjau satu nutrien.

Daftar riwayat JSON memuat `ok`, `items`, `page`, `pages`, `total`, `notices`, `url`, dan `html`. `html` memuat hasil serta paginasi; `url` menyimpan filter dan nomor halaman aktual. `q` mencari nama produk atau merek dengan `icontains` pada produk aktif. Tanggal `dari`/`sampai` inklusif, berformat `YYYY-MM-DD`; tanggal tidak valid diabaikan dengan pemberitahuan. Penyaringan tanggal mengikuti zona waktu Django proyek (saat ini UTC). Filter shelf hanya menerima shelf milik pengguna atau publik.

## Kontrak untuk Daffaa: tombol “Pilih produk ini”

Tabel pembanding mengirim `POST /riwayat/tambah/` sebagai form atau FormData:

- `product`: ID produk, wajib dan aktif.
- `shelf`: ID shelf asal, opsional. Shelf harus milik pengguna atau publik, dan produk harus menjadi item shelf tersebut.
- `note`: alasan opsional, maksimal 500 karakter.
- CSRF melalui `csrfmiddlewaretoken` atau header `X-CSRFToken`; sertakan sesi pengguna dan `Accept: application/json`.

Respons sukses adalah 201:

```json
{"ok": true, "message": "Keputusan disimpan.", "item": {"id": 1, "product_id": 7, "product_name": "Produk contoh", "shelf_id": 2, "shelf_name": "Shelf contoh", "note": "Pilihan hari ini", "created_at": "2026-10-26T03:00:00+00:00"}}
```

Tanpa shelf, `shelf_id` bernilai null dan nama tampil “Tidak diketahui”. Setelah produk/shelf dihapus, FK Decision menjadi null dan catatan tetap tersedia. Produk nonaktif juga ditampilkan “Tidak diketahui”, tanpa menghapus riwayat. Penyuntingan keputusan hanya mengubah alasan; field pemilik, produk, dan shelf pada POST ubah diabaikan. Endpoint tambah tidak membuat ulang model milik app lain dan tidak memanggil API eksternal.

Untuk hapus massal kirim, misalnya, `ids=1&ids=2`. ID duplikat dihitung sekali. Seluruh pilihan diperiksa sebelum penghapusan dalam satu transaksi; satu pilihan asing/hilang membatalkan seluruh operasi. Respons sukses: `{"ok": true, "message": "2 keputusan dihapus.", "deleted_ids": [1, 2]}`. UI menyediakan checkbox untuk catatan pada halaman aktif.

Tombol di template shelf belum dipasang oleh modul ini karena merupakan file Daffaa. Integrasi tombol dan percobaan di PWS tetap perlu dilakukan bersama pemilik Modul 2.

## Memasang ranking pada tabel pembanding

`ranking.py` tidak mengimpor model, request, atau ORM. Pemanggil memuat produk aktif dan preferensi pengguna terlebih dahulu; fungsi hanya mengolah iterable objek yang diterima.

```python
from preferences.ranking import order_metric_rows, rank_products

# products sudah dibatasi ke produk aktif dalam shelf yang boleh dibuka.
saved_preferences = list(request.user.nutrition_preferences.all()) if request.user.is_authenticated else []
products = rank_products(products, saved_preferences)
metric_keys = order_metric_rows(
    saved_preferences,
    ["energy", "protein", "saturated_fat", "sugar", "fiber", "sodium"],
)
```

`order_metric_rows` mendahulukan nutrien preferensi berbobot besar; seri mengikuti urutan bawaan. Key di luar enam nutrien dipertahankan di belakang. `rank_products` menjumlahkan skor min-max berbobot; arah min dibalik. Nilai None tidak menyumbang skor dan tidak diubah menjadi nol. Bila nilai satu nutrien semuanya sama, setiap nilai diketahui mendapat kontribusi 1 × bobot. Produk tanpa data pada seluruh nutrien preferensi berada terakhir, secara stabil. Tanpa preferensi, urutan produk tetap.

`shelves/comparison.py` saat ini mengembalikan dictionary baris dengan `label`, bukan key nutrien. Daffaa perlu memetakan label melalui `NUTRIENT_FIELDS`, lalu menyusun baris sesuai `metric_keys`. Grade, NOVA, kemasan, asal, lemak total, dan karbohidrat tetap ditangani oleh Modul 2. Jika kolom produk diurutkan, lakukan sebelum `comparison_rows(products)` agar sel tetap selaras dengan produk. Modul ini menyediakan fungsi dan tes, belum mengubah view/template shelf.

## Rate limit dan pembaruan optimistik

Enam endpoint CRUD tulis dan endpoint hapus massal memakai batas gabungan 30 request per 60 detik per pengguna. Request invalid yang sudah mencapai limiter juga dihitung; GET tidak dihitung. Pemeriksaan login, metode, dan pemilik pada ubah/hapus tunggal berjalan sebelum limiter. Respons 429 membawa `Retry-After: 60` dan pesan ramah.

Limiter memakai cache bawaan Django. Konfigurasi saat ini adalah LocMemCache: hitungan berlaku per proses dan hilang saat proses restart atau entri cache dibuang. Ini pembatas sederhana, bukan kuota global antar-worker. Tidak ada dependency Redis, perubahan settings, atau klaim batas global di produksi. Cache bersama memerlukan koordinasi dengan pemilik konfigurasi proyek.

Toggle berubah secara visual saat request dikirim; bobot/arah yang baru dipilih terlihat segera. Penghapusan tunggal/massal menyembunyikan baris sementara. Kontrol yang berkaitan dinonaktifkan selama request untuk menghindari pengiriman bersamaan. Toast sukses hanya muncul setelah server menyetujui. Kegagalan mengembalikan toggle/bobot/arah, menampilkan lagi baris yang disembunyikan, dan mengembalikan alasan ke nilai tersimpan terakhir. Fokus keyboard dipulihkan setelah penggantian DOM. Bila mutasi sukses tetapi refresh daftar gagal, pesan menjelaskan bahwa penyimpanan berhasil dan daftar perlu dimuat ulang. Putus koneksi setelah server menyimpan tetap dapat membuat hasil lokal tidak pasti; muat ulang untuk memeriksa database.

## Peta kode untuk demo

**`constants.py`** menyimpan enam pemetaan nutrien, label/satuan/skala, pilihan arah/bobot, default, serta batas rate limit. Perbedaan field Product cukup ditangani di pemetaan ini. Natrium memakai gram di database dan mg pada pratinjau.

**`models.py`** mendefinisikan Preference yang unik per pengguna/nutrien serta Decision dengan relasi SET_NULL. Validator bobot dan panjang alasan menjaga validasi model; `max_length` TextField dilengkapi MaxLengthValidator agar `full_clean()` juga menolak alasan panjang. `__str__` tetap berjalan saat relasi produk kosong.

**`forms.py`** memvalidasi duplikasi preferensi dan mengunci nutrien saat edit. DecisionForm membatasi pilihan produk aktif dan shelf terlihat, lalu memeriksa keanggotaan produk. Edit keputusan hanya menampilkan alasan. DecisionFilterForm membersihkan query/tanggal; DecisionBulkDeleteForm membersihkan daftar ID, membatasi 100 pilihan, dan membuang duplikat.

**`decorators.py`** menentukan permintaan JSON, membatasi metode, memeriksa pemilik, dan menerapkan rate limit per pengguna. Pemilik yang berbeda menerima 403; ID yang tidak ada menerima 404. Wrapper memakai `wraps` agar metadata view tetap terbaca Django.

**`views.py`** menghubungkan form, ORM, dan respons. Daftar selalu dibatasi ke pengguna aktif. Pratinjau serta filter dilakukan di database sebelum paginasi. Serializer membentuk JSON yang stabil dan mengganti relasi kosong dengan label netral. Hapus massal memakai transaksi dan memeriksa seluruh pemilik sebelum query delete.

**`urls.py`** menyediakan namespace `preferences` dan sepuluh URL dalam tabel di atas. Root URL proyek hanya menambahkan satu include modul.

**`ranking.py`** mengurutkan metrik dan produk tanpa database. Fungsi menerima data yang sudah dimuat, tidak mengubah objek input, dan memakai sort stabil untuk nilai seri atau data kosong.

**`admin.py`** mendaftarkan kedua model untuk admin Django. Akses admin mengikuti autentikasi dan otorisasi admin bawaan proyek.

**`apps.py`** mendaftarkan app `preferences`. **`__init__.py`** menandai paket Python dan tidak menjalankan logika tambahan.

**`migrations/0001_initial.py`** membuat tabel, FK, dan constraint. **`migrations/0002_alter_decision_note.py`** mencatat validator panjang alasan tambahan. Keduanya sudah diterapkan lokal; migrasi yang telah dibuat tidak ditulis ulang.

**`templates/preferences/preference_list.html`** mewarisi base, menampilkan daftar enam nutrien, status/error, tautan riwayat, dan script modul.

**`templates/preferences/_preference_row.html`** menampilkan segmented control bobot, select arah, switch aktif, dan pratinjau. Data attribute menyimpan keadaan server terakhir untuk rollback. Radio/select nutrien nonaktif benar-benar disabled.

**`templates/preferences/decision_list.html`** menampilkan form pencatatan dan filter serta region hasil. Label form filter mempunyai ID berbeda dari form pencatatan. Script dimuat pada akhir block content.

**`templates/preferences/_decision_results.html`** merender pemberitahuan, jumlah hasil, form hapus massal, baris, dan tautan paginasi yang membawa filter. Partial yang sama dipakai untuk halaman awal dan JSON AJAX.

**`templates/preferences/_decision_row.html`** menampilkan produk/shelf/tanggal, checkbox yang dihubungkan ke form massal, textarea alasan, dan tombol ubah/hapus. Teks pengguna di-escape Django; tanggal ISO tersedia pada atribut time.

**`templates/preferences/_forbidden.html`** menyediakan halaman 403 untuk akses data milik pengguna lain, dengan tautan kembali ke profil.

**`templates/preferences/_error.html`** menampilkan kegagalan hapus massal atau rate limit pada alur HTML. Status HTTP tetap mengikuti penyebab kesalahan.

**`static/js/preferences.js`** mengirim FormData dan header CSRF, memproses JSON, mengganti partial HTML server, dan memanggil toast bersama. Filter memakai debounce serta `history.replaceState`; nomor request mencegah respons lama menimpa hasil lebih baru. Tidak memakai localStorage/sessionStorage.

**`tests/helpers.py`** membuat User/Product/Shelf/ShelfItem yang sesuai model asli; `build_product` membuat objek tanpa penyimpanan untuk tes fungsi murni. Tes tidak bergantung pada fixture seed.

**`tests/test_models.py`** memeriksa default, validator, keunikan, urutan keputusan, dan kelangsungan riwayat setelah relasi dihapus. **`tests/test_forms.py`** menguji duplikasi, bobot, shelf terlihat, keanggotaan produk, dan produk aktif.

**`tests/test_views_preference.py`** menguji alur HTML/JSON, preferensi tersimpan, kontrol nonaktif, validasi, dan pratinjau termasuk NULL/0/natrium. **`tests/test_views_decision.py`** menguji CRUD, filter/paginasi/tanggal, relasi kosong, serta penolakan field palsu saat edit alasan.

**`tests/test_authorization.py`** menguji pengunjung, akses lintas pengguna, ID hilang, dan CSRF di seluruh endpoint tulis. **`tests/test_hardening.py`** menguji quota per pengguna, masa berlaku, serta hapus massal tanpa penghapusan parsial.

**`tests/test_ranking.py`** menguji skor dan urutan murni, termasuk arah, bobot, nol, kosong, seri, dan iterable. **`tests/test_functional.py`** menjalankan tiga alur browser opsional menggunakan Playwright dan Chrome lokal. Tes browser tidak menambah dependency produksi.

**`NOTES.md`** adalah panduan kontrak, demo, validasi, dan disclosure untuk pemilik modul. Dokumen kelompok dan instruksi pribadi di root tidak ikut diubah.

Alur request contoh: pengguna mengubah bobot Protein → event change mengirim form lewat fetch dengan CSRF → Django memeriksa sesi/metode/pemilik/rate limit → PreferenceForm memvalidasi arah/bobot → ORM memperbarui Preference → view mengirim item dan partial HTML → JavaScript mengganti baris, memulihkan fokus, dan menampilkan toast. Bila validasi/request gagal, JavaScript mengembalikan keadaan kontrol tersimpan. Tanpa JavaScript, form POST tetap diproses dan diarahkan kembali ke halaman.
