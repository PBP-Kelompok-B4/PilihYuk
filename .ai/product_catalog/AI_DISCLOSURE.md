# AI Disclosure — Modul Katalog Produk PilihYuk

**Developer:** Yasmin · 2506606124  
**App Django:** `product_catalog`  
**Diperbarui:** 1 November 2026

## A. Gambaran umum penggunaan AI

Saya menggunakan OpenAI Codex sebagai asisten selama pengerjaan modul Katalog Produk. Penggunaan Codex sebagai satu-satunya alat AI untuk pekerjaan saya telah saya konfirmasi dalam percakapan penyusunan dokumen ini. AI membantu proses pengembangan dan dokumentasi; keputusan kebutuhan, penerimaan perubahan, integrasi dengan modul tim, dan verifikasi akhir tetap menjadi tanggung jawab saya. Saya tidak mengklaim bahwa seluruh kode ditulis secara mandiri tanpa bantuan AI.

Modul ini menyediakan katalog dan detail produk, pencarian serta filter database, penambahan lewat barcode atau form manual, penyuntingan dan soft delete sesuai hak akses, serta riwayat produk yang dilihat. Data eksternal berasal dari Open Food Facts (OFF), sedangkan antarmuka memakai template Django dan JavaScript untuk pencarian/filter AJAX. Konteks aplikasi dan setup tersedia pada [README proyek](../../README.md).

Dokumen ini menggunakan konfirmasi developer, transkrip yang dilampirkan pada 1 November 2026, serta implementasi, tes, dan catatan proyek. Lima lampiran berisi empat transkrip unik: lampiran pertama dan kelima identik berdasarkan SHA-256. Cuplikan chat tentang form dan commit juga tersedia langsung dalam pesan developer. Tautan web percakapan tetap gagal dimuat, tetapi isi lampiran kini menyediakan bukti primer yang dapat dibaca. Identitas lampiran dan batas pemetaannya dijelaskan pada bagian G.

## B. Tools AI yang digunakan

| Alat | Tujuan penggunaan | Aktivitas yang dapat dijelaskan dari bukti |
|---|---|---|
| **OpenAI Codex** | Pair programmer, asisten audit, implementasi, debugging, pengujian, dan pembelajaran | Transkrip mencatat bantuan implementasi model/migrasi, helper OFF, mapping, fixture/seed, lookup runtime, perbaikan mobile, review, serta penyusunan panduan memahami kode untuk live coding |

Model spesifik dan persentase kode hasil AI tidak dicantumkan karena tidak tersedia bukti yang memadai. Tautan berbagi ChatGPT pada bagian G merupakan referensi percakapan yang disediakan developer, bukan dasar untuk menambahkan alat AI lain.

**Atribusi kerja tim:** [README proyek, disclosure Daffaa](../../README.md#ai-disclosure) mencatat penggunaan Claude Code oleh Daffaa untuk riset OFF dan pekerjaan bersama, termasuk pemindahan seed dan tes Modul 1 ke paket terpisah. Hal tersebut tidak dinyatakan sebagai penggunaan Claude oleh saya. Temuan riset tim dipakai sebagai konteks teknis bersama; dokumen ini tidak mengatribusikan seluruh riset OFF, pemilihan SDK, atau refaktor struktur kepada Codex/Yasmin.

## C. Area pengembangan yang mendapat bantuan AI

Transkrip T1–T4 pada bagian G menunjukkan bahwa Codex tidak hanya memberi penjelasan, tetapi juga membantu menulis dan mengubah kode serta tes. Tabel berikut menghubungkan pekerjaan tersebut dengan implementasi saat ini. Kontribusi ini tidak berarti seluruh modul, riset, atau kode bersama dibuat oleh Codex.

| Area dan permasalahan | Bantuan Codex dalam transkrip | Evaluasi dan hasil yang dapat diperiksa |
|---|---|---|
| **Integrasi OFF:** respons gagal tidak selalu JSON; produk hasil lookup belum tentu dijual di Indonesia | Mengintegrasikan draft helper dan mapping dari konteks tim (T1), lalu memperketat validasi payload malformed dan grade invalid (T2) | Developer meminta timeout 10 detik dan prioritas field sesuai PRD dipertahankan. [Klien OFF](../../product_catalog/open_food_facts.py) kini membedakan not-found dari struktur invalid; [mapping](../../product_catalog/seed/off_mapping.py) mensyaratkan bukti negara |
| **Dataset dan fixture:** impor harus dapat diulang tanpa menimpa data lokal | Membuat fixture riset 20 produk dari sampel tersimpan dan loader aman (T1); membantu menjelaskan finalisasi 406 serta keterbatasan dataset (T2/T3) | Audit meninjau provenance, nol nutrien, impor berulang, dan preservasi ID/data lokal. [Handoff dataset](FINAL_406_HANDOFF.md) dan [tes dataset](../../product_catalog/test_suites/test_final_dataset.py) menjelaskan kebijakan final yang terpisah dari runtime |
| **Backend dan validasi:** model dan lookup perlu mengikuti kontrak proyek | Membantu implementasi Product/ProductView, migrasi dan tes (T1), serta limiter, form GTIN dan lookup (T2) | Developer menetapkan JSON kosong `[]`, timestamp sinkronisasi awal `NULL`, riwayat berulang, lalu menyetujui aturan limiter dan migrasinya. Bukti kini ada pada [model](../../product_catalog/models.py), [form](../../product_catalog/forms.py), [lookup](../../product_catalog/lookup.py), dan [tes runtime](../../product_catalog/test_suites/test_runtime.py) |
| **AJAX dan pengujian:** respons lama dapat menimpa hasil pencarian terbaru | Membaca skenario tes untuk membedakan simulasi otomatis dari uji browser | [Tes JavaScript](../../product_catalog/test_suites/test_catalog_client.cjs) mensimulasikan respons sukses/gagal yang tidak berurutan terhadap [skrip katalog](../../static/js/product_catalog.js) |
| **Tampilan responsif:** form dan teks panjang dapat melebar pada ponsel | Membantu perbaikan mobile; laporan historis menyebut penanganan header pada lebar 320 px (T3) | Developer meminta panduan cek localhost, kemudian membalas “aman”. [Template](../../templates/product_catalog/product_detail.html) dan [form](../../product_catalog/forms.py) dapat ditinjau; balasan tersebut bukan bukti uji semua perangkat |

## D. Strategi prompting dan kolaborasi developer dengan AI

Transkrip lampiran menambahkan contoh strategi prompt yang benar-benar digunakan:

- **Audit sebelum implementasi (T1):** “First understand the repository and project documentation before we implement anything.” Saya menetapkan PRD, ERD, handoff, dan implementasi sebagai sumber pemeriksaan, serta meminta konflik dilaporkan sebelum perubahan.
- **Milestone kecil (T1):** alur yang diminta adalah “AUDIT → UNDERSTAND → SMALL IMPLEMENTATION → TEST → REVIEW DIFF → COMMIT → NEXT MILESTONE”. Implementasi model dibatasi pada model, tes, dan migrasi awal.
- **Review terhadap asumsi (T1):** setelah implementasi, saya meminta pemeriksaan khusus apakah `source` wajib dan default grade/halal merupakan requirement eksplisit atau inferensi. Kelulusan tes tidak saya jadikan satu-satunya dasar penerimaan.
- **Debugging terarah (T2):** saya memberi contoh payload `[]`, `None`, dan `{"product": "invalid"}`, meminta pembedaan not-found/malformed, serta tes regresi tanpa mengubah kontrak timeout, retry, atau prioritas field.
- **Keputusan desain eksplisit (T2):** saya menyetujui sliding window 60 detik, batas tiga lookup, pengecualian lookup lokal dari kuota, perhitungan kegagalan, dan reservasi atomik sebelum jaringan. Migrasi limiter disetujui terpisah dengan syarat Product tetap dan tanpa dependency baru.

Contoh ini menunjukkan siklus konteks → usulan → keputusan developer → implementasi → review/pengujian. Permintaan penjelasan dan review adalah bukti keterlibatan; dokumen tidak mengubahnya menjadi klaim bahwa semua kode ditulis sendiri.

## E. Evaluasi kritis dan keterbatasan AI

### 1. Informasi layanan eksternal perlu diuji, bukan diasumsikan

[Temuan API tim](off-api-findings.md) mencatat bahwa subdomain `id` menyaring search tetapi tidak menyaring pembacaan barcode v3, serta bahwa nama field skor lingkungan pada API dan dump berbeda. [Evaluasi SDK tim](off-sdk-evaluation.md) mendasari pilihan klien `requests` dengan kebutuhan filter negara dan penanganan error. Implementasi memakai pemeriksaan `countries_tags` serta fallback `environmental_score_grade`/`ecoscore_grade`.

Ini merupakan contoh penyesuaian terhadap perilaku layanan yang didukung bukti proyek. Namun, README mengatribusikan koreksi asumsi AI pada riset tersebut kepada Daffaa; saya tidak mengklaimnya sebagai kesalahan Codex yang saya perbaiki sendiri. Dokumentasi riset bertanggal 2 Oktober 2026 juga bukan bukti bahwa API eksternal tidak berubah setelah tanggal itu.

### 2. Data yang terlihat wajar belum tentu memiliki makna yang benar

Pemetaan OFF mempertahankan nol gizi yang sah, membedakannya dari nilai tidak tersedia, menyimpan sodium dalam gram, dan memisahkan skor resmi dari estimasi. Form menolak angka negatif/tidak finite. Penanganan ini penting ketika menilai saran AI: mengganti nilai kosong dengan nol atau mencampur satuan dapat menghasilkan tampilan yang masuk akal tetapi menyesatkan. Rujukan implementasinya adalah [mapping](../../product_catalog/seed/off_mapping.py), [form](../../product_catalog/forms.py), dan [tes nilai model](../../product_catalog/tests.py).

Keberadaan perlindungan tersebut tidak membuktikan bahwa AI sebelumnya membuat kesalahan itu. Dokumen ini menyebutnya sebagai batas yang harus dipertahankan dalam evaluasi hasil AI, bukan insiden yang direka.

### 3. Solusi otomatis harus mengikuti batas keputusan data

[Handoff dataset](FINAL_406_HANDOFF.md) mencatat 62 pengecualian barcode yang disetujui untuk seed saja. Runtime tetap menolak seluruh 889 barcode dalam daftar pengecualian dan dapat mengimpor produk di luar manifest. Karena itu, 406 anggota fixture tidak berarti katalog runtime tertutup pada 406 produk.

Catatan yang sama menyatakan sinkronisasi lokal hanya mengubah status aktif dan timestamp. Nilai lokal Pringles ID 45 tetap `unknown` walaupun sumber memiliki grade `e`. Ini menunjukkan batas keputusan manusia yang konkret: persetujuan sinkronisasi status tidak memberi izin menimpa seluruh atribut. Persetujuan tercatat tersebut dibedakan dari klaim bahwa saya mengetik perbaikannya secara manual.

### 4. Koreksi terhadap hasil Codex yang terdokumentasi

**Validasi payload belum lengkap (T2).** Setelah MVP awal dilaporkan lulus 50 tes katalog dan 87 tes proyek, audit menemukan helper masih mengasumsikan JSON berbentuk dictionary. Payload top-level list/`None` dapat memicu perilaku tak terkendali, sementara `product` berupa list/string dapat lolos. Saya meminta hardening khusus dan tes regresi. Respons penyelesaian melaporkan `ValueError` untuk struktur malformed, `None` hanya untuk not-found eksplisit, serta penolakan grade invalid seperti `"null"`; hasil historis setelah perubahan adalah 56 tes katalog dan 93 tes proyek. Ini contoh konkret keluaran sebelumnya yang masih membutuhkan debugging, bukan sekadar risiko hipotetis.

**Pernyataan kesiapan terlalu luas (T1).** Codex semula menyatakan milestone model siap direview/commit. Setelah saya meminta source-of-truth review, jawabannya mengakui bahwa requiredness `source`, default model grade `unknown`, dan default halal `False` adalah inferensi yang konsisten dengan kebutuhan, bukan deklarasi eksplisit dokumen. Pernyataan kesiapan kemudian dibatasi pada penerimaan pilihan tersebut. Koreksinya berupa review dan klarifikasi requirement, bukan klaim edit manual oleh developer.

**Istilah “bug wajib” tidak didukung temuan (T3).** Ketika saya menanyakan maksud rekomendasi itu, Codex mengakui belum menemukan bug tertentu dan memperbaikinya menjadi instruksi menguji fitur wajib serta memperbaiki error jika ditemukan. Tindak lanjut ini mencegah rencana pekerjaan dibaca sebagai laporan kerusakan aktual.

**Validasi terhambat environment (T2).** Post-push verification melaporkan perintah Django gagal karena interpreter dan `SECRET_KEY` tidak tersedia; tes belum berjalan pada percobaan itu. Sinkronnya Git lokal/remote tidak dipakai sebagai bukti aplikasi lulus tes. Hasil pengujian berikutnya harus dibaca pada konteks eksekusinya masing-masing.

### 5. Tes dan ringkasan AI mempunyai batas pembuktian

Tes AJAX mensimulasikan urutan respons, tetapi tidak membuktikan layout, fokus keyboard, atau perilaku semua browser. Tes berbasis mock juga tidak membuktikan kondisi jaringan/API nyata. Hasil otomatis perlu dibandingkan dengan kebutuhan proyek dan bukti sumber, karena tes dapat mengikuti asumsi implementasi yang sama-sama keliru.

Tautan web tetap tidak terbaca, tetapi lampiran menyediakan contoh prompt dan iterasi di atas. Sebagian transkrip merujuk attachment lain yang isinya tidak ikut tersalin. Karena itu, riwayat yang tersedia tidak diperlakukan sebagai log lengkap seluruh tool call atau bukti penulis setiap baris kode.

## F. Verifikasi manual dan tanggung jawab developer

| Jenis verifikasi | Bukti yang tersedia | Batas kesimpulan |
|---|---|---|
| Automated testing | Suite pada `tests.py`, `test_suites/`, dan tes JavaScript | Keberadaan tes menunjukkan skenario yang dicakup; tidak sama dengan hasil eksekusi terbaru |
| Pengujian historis proyek | README melaporkan 525 tes lulus, 7 tes browser preferences dilewati tanpa Chrome, dan cakupan sekitar 93% | Ini laporan proyek yang sudah ada; suite tidak dijalankan ulang dalam tugas dokumentasi ini |
| Validasi API | Temuan tim dan respons tersimpan di [helpers/off-samples/](helpers/off-samples/) | Bukti riset historis tim, bukan pengujian langsung oleh Yasmin pada sesi ini |
| Dataset/fixture dan database lokal | Handoff mencatat validasi manifest/CSV, impor berulang, pemeriksaan integritas/FK, dan sinkronisasi ulang tanpa perubahan | Tidak membuktikan kondisi database PWS atau semua database anggota |
| Review kode dan integrasi | Form, model, view, template, dan tes ditinjau saat menyusun dokumen | Review statis tidak menggantikan menjalankan alur aplikasi |
| Pemeriksaan localhost oleh Yasmin | T3 memuat permintaan langkah cek localhost, panduan pada lebar 320/360/390 px dan alur katalog/form/riwayat, lalu balasan developer “aman” | Mendukung konfirmasi manual umum; tidak tersedia screenshot atau hasil individual tiap skenario |
| Pemeriksaan browser historis berbantuan AI | T3 melaporkan 30 kombinasi halaman/ukuran 320–1280 px tanpa overflow, AJAX/validasi form lulus, dan 207 tes tanpa kegagalan dengan 1 dilewati | Laporan hasil dari transkrip, bukan eksekusi ulang atau bukti uji ponsel fisik/PWS |

Untuk verifikasi ulang, ikuti setup pada [README proyek](../../README.md), lalu dari root proyek dengan environment aktif:

```powershell
python manage.py check
python manage.py test product_catalog
node product_catalog/test_suites/test_catalog_client.cjs
```

Tes integrasi CSV memerlukan berkas eksternal melalui `PILIHYUK_FINAL_CSV`; perhatikan tes yang dilewati dan instruksi pada handoff. Perintah di atas adalah panduan reproduksi, bukan catatan eksekusi dalam tugas ini. Tidak ada impor atau sinkronisasi database kerja dilakukan untuk menulis disclosure.

Sebagai developer, saya bertanggung jawab memeriksa perubahan sebelum menerima hasil bantuan AI, memastikan aturan data dan hak akses sesuai kebutuhan tim, serta membedakan hasil pengujian otomatis dari pemeriksaan manual. Dokumen ini tidak mengklaim semua implementasi bebas bug atau sudah diuji di deployment.

## G. Log interaksi AI yang representatif dan referensi

### Sumber transkrip yang dilampirkan

Label berikut merujuk berkas `Pasted text.txt` yang diberikan developer dalam sesi dokumentasi. ID dicantumkan agar sumber dapat dibedakan tanpa memasukkan transkrip mentah atau path pribadi ke repositori.

| Label | ID lampiran | Cakupan |
|---|---|---|
| T1 | `966448e0-83ea-4c89-8bd2-f365263f80cf` | Audit awal, keputusan skema, milestone model, review requirement, integrasi draft OFF dan katalog MVP |
| T2 | `aa73a676-00d3-402c-8fcd-3d81a7ea514f` | Verifikasi post-push, audit gap, hardening respons, keputusan limiter/GTIN, implementasi lookup, dan panduan pemeriksaan/deployment |
| T3 | `7d93c462-59c7-4b5f-8398-0d368d9da5f8` | Review progres, kualitas dataset, koreksi istilah bug, perbaikan mobile, panduan localhost, dan konfirmasi “aman” |
| T4 | `3d952a46-1140-4dc6-b1d2-38b541251d23` | Permintaan panduan memahami modul untuk live coding dan laporan penyusunannya |
| Duplikat T1 | `3952f8ab-9645-4ae4-a6e2-146be3418a68` | Konten identik dengan T1 menurut SHA-256; tidak dihitung sebagai bukti independen |
| Cuplikan pesan langsung | Pesan developer yang menyertai lampiran | Pertanyaan kebutuhan add-product, validasi form kosong, serta review scope commit dokumentasi |

### Interaksi pengembangan

| Topik | Bentuk bantuan AI | Peran atau keputusan developer | Referensi |
|---|---|---|---|
| Model dan migrasi | Implementasi Product/ProductView serta tes; laporan 23 tes model lulus | Menetapkan kontrak JSON/timestamp/riwayat, membatasi file, dan meminta review inferensi | T1 |
| OFF dan fixture MVP | Integrasi helper, mapping, 20 produk, loader dan katalog | Meminta provenance, perlindungan data lama, audit ulang dan pelaporan gap | T1 |
| Respons malformed | Audit bug, hardening dan enam tes regresi dengan subcase | Memberi kasus input, menetapkan kontrak error dan batas perubahan | T2 |
| Limiter lookup | Menjelaskan kebutuhan storage bersama dan mengimplementasikan reservasi kuota | Menyetujui window, hitungan kuota, migrasi, atomisitas, dan larangan transaksi selama jaringan | T2 |
| UI dan localhost | Perbaikan mobile serta langkah pemeriksaan | Meminta panduan cek sendiri dan memberi konfirmasi “aman” | T3 |
| Pemahaman kode | Panduan eksekusi, integrasi, rekonstruksi, latihan dan debugging | Meminta pembahasan mendalam modul sendiri dan batas atribusi yang jujur | T4 |
| Form dan keamanan | Review required field, validasi server, CSRF dan hak akses | Menanyakan input kosong dan kecocokan add-product dengan PRD | Cuplikan pesan langsung |

Pada cuplikan form, AI secara eksplisit menyebut tes baru diperiksa isinya, belum dijalankan ulang. Pertanyaan input kosong membahas salah satu kontrol validasi; jawaban tersebut tidak mengklaim audit cybersecurity menyeluruh.

### Percakapan penyusunan disclosure

Berikut log yang dapat diverifikasi dari percakapan penyusunan yang tersedia:

| Topik | Bentuk bantuan AI | Peran/keputusan developer | Referensi |
|---|---|---|---|
| Penyusunan disclosure modul | Pemeriksaan dokumen dan kode untuk membuat penjelasan berbasis bukti | Menetapkan rubrik, modul, lokasi keluaran, serta larangan commit | Percakapan penyusunan disclosure ini |
| Identifikasi alat | Menyesuaikan pernyataan alat berdasarkan konfirmasi pengguna | Menyatakan hanya memakai Codex selama pengerjaan | Balasan developer pada percakapan penyusunan |
| Audit riwayat dan batas perubahan | Mencoba membaca enam tautan, memeriksa implementasi terkini, dan mencatat keterbatasan akses | Menyediakan tautan dan menetapkan hanya `AI_DISCLOSURE.md` yang boleh berubah | Instruksi lampiran untuk tugas ini |

### Link chat

| Referensi percakapan | Topik, bantuan AI, dan keputusan developer | Status akses |
|---|---|---|
| [Percakapan 1](https://chatgpt.com/s/cx_6ae61ca132e4819189a75ff421be4931)
| [Percakapan 2](https://chatgpt.com/s/cx_6ae61caf28948191ad0121e04aceae8e)
| [Percakapan 3](https://chatgpt.com/s/cx_6ae61cbf347481919a69da0e51211ef9)