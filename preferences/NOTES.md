# Modul 5 — Preferensi Nutrisi dan Riwayat Keputusan

Pemilik: Jonathan Sebastian Sindhu. Pembaruan pekerjaan lanjutan: 27 Oktober 2026.

## Acuan dan kondisi implementasi

Acuan berkas tim: [PRD](../.claude/PRD.md), [HANDOFF](../.claude/HANDOFF.md), [timeline](../.claude/timeline.md), serta [README proyek](../README.md). First brief adalah arsip. Status Modul 5 dalam handoff/timeline tanggal 24 Oktober mendahului implementasi; kode dan tes menunjukkan S1–S11 telah selesai sebelum pekerjaan lanjutan ini.

Tailwind v4 memakai script CDN `@tailwindcss/browser` yang sudah dimuat base. Tema/komponen ada di `templates/components/tailwind.html`. Tidak ada build, binary CLI, CDN kedua, atau perubahan output.css. Internet diperlukan untuk memuat CDN saat demo. Header/footer/tema, settings, requirements, README dan app teman tetap dipakai tanpa diubah.

AGENTS.md pribadi telah diperbarui atas izin pengguna: draft global menggantikan penyimpanan langsung kontrol UI, Reset mengosongkan draft, pratinjau gabungan, field konteks Decision, modal/kartu baca, ekspor, pengujian, dan CDN. AGENTS.md tetap di-exclude dan tidak di-commit. Setup/seeding tidak diulang karena environment sudah tersedia. Sinkronisasi origin/dev menyatakan already up to date.

Seluruh commit dan penanda S1–S11 dipertahankan. Penanda lanjutan baru:

| Penanda | Isi |
|---|---|
| `feat/preferences-followup-comparison-context` | Field dan validasi jumlah subset pembanding historis |
| `feat/preferences-followup-draft-api` | Simpan global atomik dan pratinjau gabungan |
| `feat/preferences-followup-history-api` | Privasi shelf historis, ringkasan, filter bulan, CSV |
| `feat/preferences-followup-preference-design` | Tampilan preferensi dengan draft, Reset, sidebar |
| `feat/preferences-followup-history-design` | Kartu baca, modal tambah/edit, konfirmasi, states |
| `feat/preferences-followup-regression` | Rollback storage, CSV, keamanan endpoint baru |
| `feat/preferences-followup-docs` | Kontrak, peta demo, dan hasil akhir lanjutan |

Tidak ada push atau PR oleh Codex. Dokumentasi historis sebelum perubahan tersedia melalui `git show bd76229:preferences/NOTES.md`; perilaku UI saat ini mengikuti dokumen ini.

## Preferensi: draft dan simpan global

Enam baris berurutan: Protein, Serat, Gula, Natrium, Lemak jenuh, Kalori. Label Kalori memakai key `energy` dan Product.energy_kcal_100g yang sama. Bobot Rendah/Sedang/Tinggi = 1/2/3. Default 2; arah awal Protein/Serat=max, lainnya=min. Data pengguna yang sudah tersimpan tidak diubah oleh default baru. Row Preference berarti aktif; tidak ada field status tambahan.

Perubahan switch, arah, dan bobot hanya menjadi draft di memori halaman. Tidak ada autosave UI atau tombol simpan per baris. Ringkasan dan pratinjau mengikuti draft, status menandai perubahan belum disimpan. Tombol Simpan Preferensi mengirim seluruh keadaan akhir melalui satu request. Backend memvalidasi keenam row sebelum transaksi: row aktif dibuat/diperbarui, row nonaktif dihapus pada request.user saja. Baris user dikunci saat transaksi untuk menyelaraskan simpan global. Sukses memperbarui baseline; kegagalan mempertahankan draft untuk diperbaiki/dicoba lagi.

Reset mengosongkan draft: seluruh nutrien nonaktif, bobot 2, arah default. Database belum berubah. Pesan: “Preferensi direset. Klik Simpan Preferensi untuk menerapkan perubahan.” Pengguna boleh mengaktifkan sebagian nutrien lagi sebelum Simpan; request menerapkan draft terakhir. Simpan seluruhnya nonaktif menghapus semua Preference pengguna saja, tanpa mengubah Decision. Draft yang belum disimpan hilang ketika halaman dimuat ulang; tidak ada localStorage/sessionStorage.

## Endpoint dan bentuk respons

Semua endpoint memerlukan sesi login. Pengunjung diarahkan ke Masuk dengan `?next=`. Semua POST, termasuk pratinjau gabungan yang hanya membaca, memerlukan CSRF. Endpoint lama memakai JSON bila Accept application/json atau X-Requested-With XMLHttpRequest; selain itu menyediakan alur HTML. API draft baru mengembalikan JSON.

| Metode | URL | Nama URL | Input |
|---|---|---|---|
| GET | `/preferensi/` | `preference_list` | Daftar tersimpan/halaman draft |
| POST | `/preferensi/simpan/` | `preference_save` | JSON `preferences`, enam row |
| POST | `/preferensi/pratinjau-gabungan/` | `preference_combined_preview` | JSON draft yang sama |
| GET | `/preferensi/pratinjau/` | `preference_preview` | Legacy `nutrient`, `direction` |
| POST | `/preferensi/tambah/` | `preference_create` | Legacy `nutrient`, `direction`, `weight` |
| POST | `/preferensi/<pk>/ubah/` | `preference_update` | Legacy `direction`, `weight` |
| POST | `/preferensi/<pk>/hapus/` | `preference_delete` | Legacy hapus satu row |
| GET | `/riwayat/` | `decision_list` | `q`, `shelf`, `dari`, `sampai`, `bulan`, `page` |
| GET | `/riwayat/ekspor/` | `decision_export` | Filter yang sama; page diabaikan |
| POST | `/riwayat/tambah/` | `decision_create` | Form product/shelf/note/subset |
| POST | `/riwayat/<pk>/ubah/` | `decision_update` | Form `note` saja |
| POST | `/riwayat/<pk>/hapus/` | `decision_delete` | Hapus satu keputusan |
| POST | `/riwayat/hapus-massal/` | `decision_bulk_delete` | Form field `ids` berulang |

Semua nama memakai namespace `preferences:`. Tiga endpoint baru telah disetujui pengguna. Endpoint individu dan pratinjau satu nutrien dipertahankan untuk kompatibilitas, bukan untuk autosave UI baru.

Contoh JSON draft lengkap (semua key wajib, tidak menerima duplikasi nutrien, active harus boolean, weight integer 1–3):

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

Simpan global: `{"ok": true, "message": "Preferensi disimpan.", "items": [...]}` (200). Item preferensi tetap memuat id, nutrient, nutrient_label, direction, weight. API CRUD individu tetap memakai `item` (201 untuk tambah, 200 ubah/hapus). Daftar tersimpan: `{"ok": true, "items": [...]}`. API individu juga menyediakan partial HTML untuk pemanggil yang sudah memakainya.

Validasi 400 memakai `{"ok": false, "message": "...", "errors": {"nama_field": ["..."]}}`. Bukan pemilik 403, ID hilang 404, metode salah 405, rate limit 429, dengan ok=false/message. Middleware CSRF atau error server dapat mengembalikan HTML; fetch menangani respons bukan JSON dan redirect sesi kedaluwarsa tanpa menganggap penyimpanan berhasil. Format khusus Modul 5 tetap mengikuti kontrak pengguna/Daffaa; penyatuan format dengan usulan umum SDK Flutter perlu kesepakatan tim.

## Pratinjau gabungan dan interpretasi F-5.7

ORM mengambil Product aktif dengan setidaknya satu nilai bukan NULL pada nutrien draft yang aktif. Setelah kandidat diambil, rank_products() menghitung skor dan memilih maksimal tiga. Tidak ada write Preference atau panggilan OFF. Bobot memengaruhi ranking gabungan; pratinjau satu nutrien lama tetap tidak menggunakan bobot.

Respons gabungan memuat ok, ranked_count, total_active, samples, state. State inactive berarti tidak ada preferensi aktif; empty berarti tidak ada kandidat berdata; ready berarti hasil tersedia. Setiap sampel berisi id, name, dan values (label/value/unit per nutrien aktif). None tetap null, nol tetap 0, natrium dikali 1000 ke mg; nilai ditampilkan satu desimal. Respons lama ditolak melalui nomor versi request, termasuk saat draft berubah sebelum debounce selesai.

Hitungan disebut **“produk dapat diperingkat”**: kandidat dengan sedikitnya satu nilai relevan. F-5.7 PRD menyebut “lolos” tanpa ambang numerik, sehingga implementasi ini mengurutkan data dan tidak mengklaim filter ambang telah disepakati. Istilah/kriteria kelolosan masih perlu diselaraskan kelompok. Angka 7 pada gambar adalah ilustrasi, bukan konstanta implementasi.

Data parsial hanya menyumbang skor pada nutrien yang diketahui. Min-max dihitung antar kandidat untuk tiap nutrien; arah min dibalik, lalu dijumlahkan × bobot. Bila semua nilai diketahui sama, kontribusinya setara 1 × bobot. None bukan 0. Seri stabil mengikuti input yang diambil dalam urutan pk. Produk tanpa seluruh nilai relevan tidak masuk preview. Fungsi ranking umum tetap menempatkan produk tanpa data di akhir jika dipanggil langsung dengan daftar yang memuatnya.

## Kontrak Daffaa: memilih produk dan subset pembanding

POST `/riwayat/tambah/` mempertahankan form `product` wajib, `shelf` opsional, `note` opsional max500, dan CSRF. Sertakan sesi dan Accept application/json. Produk wajib aktif. Shelf bila diisi harus terlihat dan berisi produk pilihan.

Input tambahan opsional **`compared_product_ids` berupa field form berulang**, bukan string JSON atau angka count. Contoh integrasi pada tombol di halaman Shelf:

```javascript
const body = new FormData();
body.set('product', selectedProductId);
body.set('shelf', shelfId);
body.set('note', note || '');
for (const id of comparedIds) body.append('compared_product_ids', String(id));
fetch('/riwayat/tambah/', {
  method: 'POST', body,
  headers: {'Accept': 'application/json', 'X-CSRFToken': csrfToken}
});
```

`comparedIds` harus berasal dari subset tabel yang benar-benar dipilih, bukan seluruh items shelf. View Shelf saat ini memakai GET `banding` dan membatasi empat produk; JSON `/shelf/<pk>/?format=json` mengembalikan `compared`. Daftar `products` pada respons itu bisa berisi hingga 12 anggota shelf, sehingga tidak boleh digunakan sebagai subset. Sejak 28 Oktober tombol "Pilih ini" di baris Aksi tabel Shelf mengirim form ini dengan `product`, `shelf`, dan setiap ID di `compared` sebagai `compared_product_ids`. Form itu tetap berjalan tanpa JavaScript; dengan JavaScript hasilnya muncul sebagai toast.

Jika subset dikirim: shelf wajib; 1–4 ID unik tanpa duplikasi; seluruh produk aktif dan anggota shelf yang terlihat; subset mencakup produk pilihan. Backend menghitung jumlah valid dalam transaksi bersama Decision. Input `compared_product_count` dari klien diabaikan. Tanpa subset, request lama tetap berhasil dengan count=NULL. Tidak ada penebakan dari jumlah item shelf atau backfill riwayat lama.

Respons tambah (201), contoh:

```json
{"ok": true, "message": "Keputusan disimpan.", "item": {
  "id": 1, "product_id": 7, "product_name": "Produk contoh",
  "shelf_id": 2, "shelf_name": "Susu untuk kopi", "note": "Pilihan pagi",
  "created_at": "2026-10-27T03:00:00+00:00", "compared_product_count": 2
}}
```

Item juga menyediakan brand, quantity, image_url, product_url, shelf_url untuk kartu. Relasi product/shelf tetap SET_NULL seperti PRD. Edit Decision hanya mengubah note; ID pemilik/product/shelf/subset/count dari POST edit diabaikan. Jumlah tetap setelah note, preferensi, atau isi shelf berubah, serta setelah relasi dihapus. Badge N produk dibandingkan muncul hanya jika count tersedia. Form manual tidak menebak subset dan menjelaskan bahwa jumlah dapat kosong.

Validasi ID memastikan konteks yang dikirim sah saat pencatatan, bukan bukti audit isi tabel yang pernah dilihat browser. Tidak ada snapshot penuh nutrisi/kandidat, durasi keputusan, atau alasan otomatis.

## Ranking untuk integrasi Shelf

`order_metric_rows(preferences, default_rows)` mengurutkan key nutrien preferensi aktif dahulu, bobot besar dahulu, seri mengikuti urutan bawaan, key tidak dikenal di belakang. `rank_products(products, preferences)` fungsi murni untuk urutan produk. Pemanggil memuat produk aktif/shelf terlihat dan preferensi pengguna terlebih dahulu.

```python
from preferences.ranking import order_metric_rows, rank_products

priorities = list(request.user.nutrition_preferences.all()) if request.user.is_authenticated else []
products = rank_products(products, priorities)  # products sudah dimuat dari query aktif dalam shelf
metric_keys = order_metric_rows(priorities, ["energy", "protein", "saturated_fat", "sugar", "fiber", "sodium"])
```

Daftar baris dibentuk `shelves/comparison.py::comparison_rows(products, preferences)`. Fungsi itu memetakan preferensi ke kolom lewat `NUTRIENT_FIELDS[...]["field"]`, bukan lewat label, sehingga "Kalori" di halaman ini cocok dengan baris "Energi" di tabel Shelf. Baris gizi yang punya preferensi aktif naik ke atas (bobot besar dahulu) dan diberi `preferred: true`; urutan produk (kolom) tidak diubah.

Tanpa preferensi, tabel memakai arah bawaan: protein dan serat max; gula, natrium, dan lemak jenuh min; energi, lemak total, dan karbohidrat tidak diperingkat. Untuk nutrien yang punya preferensi aktif, penanda nilai terbaik mengikuti arah preferensi, jadi energi pun bisa diperingkat. Bar di atas tabel menampilkan preferensi aktif dan tautan ke halaman ini. **Integrasi tombol/subset dan pengurutan baris sudah dipasang di Modul 2 dan diuji (`shelves/tests.py`, kelas `PreferenceIntegrationTests`) pada 28 Oktober.** Modul ini tetap tidak mengubah file shelves.

## Riwayat, ringkasan, CSV, dan states

Kartu baca menampilkan tanggal, produk/shelf yang masih tersedia, gambar atau placeholder, alasan yang di-escape, tautan detail valid, dan count historis. Produk nonaktif/FK NULL tetap mempertahankan Decision tetapi metadata produk menjadi “Tidak diketahui” dan tautan produk tidak ditampilkan. Shelf yang kini privat milik orang lain disembunyikan nama, ID, dan tautannya dari HTML/JSON/CSV/chip. Pengguna tetap dapat mengubah alasan atau menghapus riwayatnya.

Form tambah/edit ada di dialog native dengan label, fokus awal, Escape, dan pengembalian fokus. Hapus tunggal/massal meminta konfirmasi dahulu. Checkbox massal mencakup halaman saat ini; API menerima 1–100 ID, membuang ID duplikat, memeriksa seluruh pemilik/keberadaan sebelum delete dalam satu transaksi. Respons `deleted_ids` dipertahankan. Alasan edit yang gagal tetap ada di dialog untuk dicoba lagi; kartu hanya berubah setelah server menyetujui.

Filter q, shelf, dari, sampai tetap lewat ORM dan dipaginasi sepuluh per halaman. q mencari nama/merek produk aktif. Tanggal inklusif, format YYYY-MM-DD; invalid diabaikan dengan pemberitahuan. `bulan=ini` membatasi bulan kalender saat ini. Waktu dan filter memakai zona Django proyek (UTC), ditampilkan dengan label zona, tanpa perubahan settings bersama. Chip Semua/Bulan ini/shelf nyata mengganti filter cepat; form memungkinkan gabungan filter. URL diperbarui melalui history.replaceState.

Ringkasan selalu seluruh riwayat pengguna: total Decision, shelf unik yang masih dapat diakses, dan produk unik dengan FK yang masih tercatat (termasuk nonaktif). Tidak dibatasi halaman/filter; relasi NULL tidak dihitung sebagai produk/shelf unik. Tidak ada statistik waktu/kebiasaan yang datanya belum disimpan.

JSON riwayat mempertahankan ok/items/page/pages/total/notices/url/html, ditambah summary, tools_html, export_url untuk memperbarui sidebar/chip/tautan ekspor. CSV memakai queryset filter yang sama tanpa paginasi: kolom id, created_at, product_name, shelf_name, note, compared_product_count. Nilai count kosong diekspor kosong. UTF-8 BOM membantu Excel; teks berawalan formula, termasuk whitespace/kontrol sebelum = + - @, diberi apostrof. Relasi NULL dan shelf privat tetap terlindungi.

Ada loading visual/aria-busy, state akun belum punya riwayat yang berbeda dari filter kosong, Bersihkan filter, error dan Coba lagi. Submit berulang dicegah. UI hanya memakai satu notifikasi visual toast; status tambahan sr-only untuk pembaca layar. Request preview/history yang kedaluwarsa tidak menimpa hasil baru. Penghapusan menyembunyikan baris sementara dan menampilkannya kembali bila gagal. Jika mutasi berhasil tetapi refresh gagal, pesan menjelaskan penyimpanan berhasil dan daftar perlu dimuat ulang.

Rate limit gabungan 30 request tulis per 60 detik per pengguna tetap berlaku, termasuk simpan global. Pratinjau gabungan adalah baca dan tidak mengambil kuota tulis walaupun POST/CSRF. Respons 429 membawa Retry-After 60. Cache bawaan saat ini LocMemCache: batas per proses, bisa hilang saat restart/eviction, bukan kuota global antar-worker. Cache bersama memerlukan koordinasi pemilik settings; tidak menambah Redis/dependency.

## Peta kode untuk demo

**constants.py**: satu pemetaan enam nutrien, label/satuan/skala dan pilihan arah/bobot; default arah per nutrien serta rate limit. Label Kalori tidak mengubah field Product. Konstanta default arah tunggal lama dipertahankan untuk kompatibilitas kode lama; UI memakai DEFAULT_DIRECTIONS.

**models.py**: Preference unik per user/nutrien, validator bobot, dan Decision dengan SET_NULL serta count nullable. MaxLengthValidator menegakkan max500 saat full_clean, bukan hanya form. __str__ aman saat product hilang.

**forms.py**: PreferenceForm menjaga API individu; PreferenceDraftForm memvalidasi keenam row sebelum write. DecisionForm memeriksa produk/shelf/subset dan membatasi edit ke note. DecisionFilterForm membersihkan query/tanggal/bulan. DecisionBulkDeleteForm memvalidasi daftar ID massal.

**views.py**: login/metode/pemilik dipasang sebelum logika; simpan draft dan Decision memakai transaksi. Preview memakai ORM lalu fungsi ranking. filtered_decisions() menyatukan filter HTML/JSON/CSV; decision_item() menyensor metadata yang tidak boleh terlihat. Context mengisi ringkasan/chip, serializer menyediakan partial HTML dan JSON stabil.

**decorators.py**: deteksi JSON, pembatasan metode, pemilik 403/404, serta limiter cache per pengguna. Metadata view dipertahankan dengan wraps. Middleware CSRF dan sesi tetap milik proyek.

**urls.py**: namespace preferences dan endpoint lama/lanjutan dalam tabel kontrak; root include yang sudah tersedia tidak diubah.

**ranking.py**: dua fungsi murni tanpa query/request/model; input iterable tidak dimutasi, None tidak dianggap nol dan seri stabil. Query kandidat berada di view.

**admin.py**: mendaftarkan kedua model pada admin Django; otorisasi admin mengikuti proyek.

**apps.py**: registrasi app preferences. **__init__.py** menandai paket Python tanpa logika tambahan.

**migrations/0001_initial.py**: tabel, FK, constraint awal. **0002_alter_decision_note.py**: validator max500. **0003_decision_compared_product_count.py**: count nullable tanpa backfill. **0004_alter_preference_nutrient.py**: label choice energy menjadi Kalori. Migrasi lama tidak ditulis ulang.

**templates/preferences/preference_list.html**: breadcrumb, banner, satu kartu enam nutrien, tombol global, sidebar summary/preview/privacy, script pada akhir content.

**templates/preferences/_preference_row.html**: radio arah/bobot, switch paling kanan, nilai/default data attributes, fieldset disabled untuk nonaktif. Tidak memuat form/tombol simpan per baris.

**templates/preferences/decision_list.html**: header tindakan, filter collapsible, region hasil/loading/error, sidebar ringkasan global dan dialog.

**templates/preferences/_history_tools.html**: chip filter nyata yang dirender ulang melalui AJAX.

**templates/preferences/_decision_results.html**: pemberitahuan, form hapus massal, kartu, paginasi berfilter dan dua keadaan kosong.

**templates/preferences/_decision_row.html**: kartu baca, tanggal, gambar, alasan di-escape, tautan yang tersedia, checkbox, tombol edit dan hapus. Tidak ada textarea edit permanen.

**templates/preferences/_decision_dialogs.html**: form tambah/edit dan konfirmasi hapus; label/fokus/Escape dan ukuran ponsel. Form manual mempertahankan subset kosong.

**templates/preferences/_forbidden.html**: panel akses data pengguna lain dengan link kembali. **_error.html**: error HTML dan limiter yang tetap menggunakan status HTTP sesuai penyebab.

**static/js/preferences.js**: fetch/CSRF/toast, draft/baseline/Reset, nomor versi preview, modal native, filter/paginasi, request ordering, rollback delete dan retry. Nama produk/nilai preview ditulis melalui textContent; partial HTML berasal dari template Django yang meng-escape input.

**tests/helpers.py**: pembuat User/Product/Shelf/ShelfItem asli dan Product tanpa save untuk ranking; tidak menggunakan fixture seed.

**tests/test_models.py**: validator, keunikan, ordering, dan SET_NULL. **test_forms.py**: duplikasi/bobot/produk aktif/visibilitas dan keanggotaan shelf.

**tests/test_views_preference.py**: kompatibilitas CRUD dan preview individu, persisted state dan disabled controls. **test_views_decision.py**: CRUD, filter, tanggal/paginasi, FK NULL dan field edit palsu.

**tests/test_comparison_context.py**: subset valid/invalid, 1–4 unik, legacy NULL dan count historis tetap setelah edit/delete.

**tests/test_draft.py**: atomisitas semua row, isolasi user, invalid payload, kegagalan storage setelah update pertama, serta preview kosong/parsial/nol tanpa write.

**tests/test_history_followup.py**: privasi setelah shelf berubah, CSV seluruh hasil, formula, NULL, ringkasan global dan batas bulan.

**tests/test_authorization.py**: guest/foreign/missing object dan CSRF termasuk endpoint baru. **test_hardening.py**: limiter/expiry dan bulk-delete atomik.

**tests/test_ranking.py**: arah, bobot, None/0, semua nilai sama, kosong, iterable dan zero-query. **test_functional.py**: enam tes Playwright/Chrome opsional untuk draft/Reset/gagal save, stale preview/retry, modal/konfirmasi, CRUD/filter/paginasi, rollback massal, keyboard dan layout.

Alur demo: ubah bobot → draft/summary berubah, preview POST membaca database → Simpan Preferensi mengirim enam row → validasi seluruh payload → transaksi user → items sukses → baseline diperbarui/toast. Gagal save mempertahankan draft. Untuk riwayat: buka modal → POST form/CSRF → validasi produk/shelf/subset → simpan Decision/count → refresh partial hasil/sidebar/filter → tutup dialog dan pulihkan fokus.

## Verifikasi 27 Oktober 2026

Gunakan environment proyek, tanpa mengubah requirements atau .env:

```powershell
.\env\Scripts\python.exe manage.py check
.\env\Scripts\python.exe manage.py makemigrations --check --dry-run
.\env\Scripts\python.exe manage.py test preferences
.\env\Scripts\python.exe manage.py test
$env:COVERAGE_FILE = Join-Path $env:TEMP 'pilihyuk-followup-coverage'
.\env\Scripts\python.exe -m coverage run --source=preferences manage.py test preferences
.\env\Scripts\python.exe -m coverage report -m --omit='preferences/migrations/*,preferences/tests/*'
```

Hasil: check tanpa error (satu check axes disenyapkan konfigurasi proyek); migrasi tidak tertinggal; 62 tes modul ditemukan, 56 lulus dan enam browser dilewati pada run standar. Tes seluruh proyek: 258 ditemukan, 251 lulus dan tujuh dilewati. Enam tes browser dijalankan terpisah dan lulus. Cakupan baris models/forms/views/ranking 100%, decorators 95%, total modul 99%. Tiga baris fallback expiry race pada cache belum dipicu. Cakupan baris bukan bukti semua race/jaringan telah diuji.

```powershell
$env:PILIHYUK_BROWSER_TESTS = '1'
.\env\Scripts\python.exe manage.py test preferences.tests.test_functional
$env:PILIHYUK_BROWSER_TESTS = '0'
```

Playwright 1.64.1 dan coverage 7.17.0 sudah terpasang sebagai paket dev lokal dari sesi sebelumnya, tanpa dependency produksi baru atau download browser. Chrome lokal dipakai. Tanpa opt-in/paket/Chrome, browser auto-skip. Tes browser memeriksa 390, 768, 1024, 1440 px tanpa overflow; screenshot memakai data tes dan disimpan sementara, bukan fixture produksi. Pengujian tidak memanggil OFF. Warning lama staticfiles/paginasi Shelf tidak diubah karena di luar kepemilikan. Proxy dan deployment PWS belum diuji pada sesi ini.

## Koordinasi dan langkah manual

1. Tinjau hasil dan lengkapi disclosure manual di bawah. AGENTS.md pribadi tetap tidak di-commit.
2. Push branch preferences dan penanda followup baru yang diperlukan; Codex tidak push atau membuat PR. Pertahankan penanda S1–S11 yang sudah dipakai.
3. Buka PR lanjutan berurutan ke dev dengan merge commit tanpa squash, minta ulasan teman. Jalankan sinkronisasi/check/tes sebelum PR jika ada perubahan dev baru.
4. Daffaa memasang subset compared pada tombol “Pilih produk ini” dan order_metric_rows pada tabel aktual. Koordinasikan dukungan arah dan aturan penandaan sel; integrasi ini belum selesai.
5. Selaraskan istilah/kriteria F-5.7 “lolos” dengan “dapat diperingkat” jika kelompok menginginkan filter ambang.
6. Terapkan migrasi baru di deployment (release proyek sudah migrate/collectstatic), lalu uji PWS dan akses CDN. Tidak ada build Tailwind. Cache rate limit global perlu koordinasi settings bila dibutuhkan.

## AI disclosure

Alat: Codex di VS Code untuk implementasi Django/JavaScript, tes, inspeksi hasil command/browser dan dokumentasi. Prompt memakai AGENTS.md pribadi, dokumen kelompok, tiga gambar desain dan spesifikasi lanjutan pengguna. Batas model/form/HTTP/browser telah ditetapkan pengguna; tes perilaku ditulis/dijalankan gagal sebelum implementasi perubahan utama, lalu commit lokal kecil hingga hijau. Penanda lama dipertahankan dan penanda followup baru ditambahkan.

Koreksi selama sesi awal: Shelf sempat belum tersedia sehingga sinkronisasi diperlukan; TextField.max_length ternyata perlu validator untuk full_clean; ID field filter shelf duplikat dan fokus saat DOM diganti perlu diperbaiki. Sesi lanjutan memperbaiki ketidaksesuaian autosave/desain menjadi draft global, serta temuan bahwa shelf historis yang berubah privat masih bisa membocorkan nama. Aturan CLI yang tertinggal diganti CDN, default arah baru dibatasi pada UI, dan tes autosave yang sudah tidak sesuai diadaptasi. Pengujian nyata juga merapikan keselarasan kolom dan modal ponsel.

Keterbatasan: dokumen kelompok bertanggal lama tidak otomatis merepresentasikan status kode. Gambar berisi angka/statistik ilustrasi yang tidak boleh dibuat tanpa data; durasi/kebiasaan/alasan otomatis tidak ditambahkan. Count subset mencatat konteks valid dari klien, bukan audit tabel historis. API Shelf/arah/penandaan masih perlu koordinasi, kuota cache per proses, dan PWS belum diuji. Kegagalan koneksi setelah server commit dapat membuat klien belum mengetahui hasil; simpan global idempoten dapat dicoba lagi, sedangkan refresh diperlukan untuk memeriksa riwayat. AI tidak mengklaim pemilik telah melakukan review/perbaikan manual; pemeriksaan pemilik tetap diperlukan untuk demo/live coding.

## Ikon nutrien (lanjutan 27 Oktober 2026)

Setiap baris memakai SVG Lucide lokal: Protein=beef, Serat=wheat, Gula=candy,
Natrium=droplets, Lemak jenuh=droplet, Kalori=flame. Bentuk mengikuti acuan
desain; tetesan untuk natrium merupakan simbol visual, bukan simbol kimia.
`_nutrient_icon.html` memilih SVG dari `templates/preferences/icons/`.
Ikon berwarna hijau pada latar mint, dekoratif (`aria-hidden`, tidak menerima
fokus); nama nutrien tetap menjadi label teks. Tidak ada dependency, CDN,
atau request ikon tambahan. Sumber: https://github.com/lucide-icons/lucide.
Lisensi dan atribusi disimpan di `preferences/LUCIDE_LICENSE.txt`.

Tes render enam ikon dijalankan merah sebelum implementasi, kemudian hijau.
Verifikasi lanjutan: check dan pemeriksaan migrasi lulus; 63 tes modul
ditemukan, 57 lulus dan enam browser dilewati pada run standar. Cakupan
models/forms/views tetap 100%. Tes seluruh proyek tidak diulang untuk
perubahan template ikon yang hanya berada di modul ini.
Dua tes browser (responsif 390/768/1024/1440 px dan pratinjau) lulus;
screenshot desktop/ponsel diperiksa. Run awal di sandbox timeout saat
menunggu Tailwind CDN, lalu lulus saat akses jaringan diizinkan.
