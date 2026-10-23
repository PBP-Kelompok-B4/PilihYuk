# Rencana reset password

Status: kode selesai 24 Oktober (4 tes di `accounts/tests.py`). Di laptop email dicetak ke terminal. Di PWS email baru terkirim setelah `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (dan opsional `EMAIL_PORT`, `DEFAULT_FROM_EMAIL`) diisi. Tanpa itu, email hanya muncul di log PWS. Belum dikerjakan: layar lupa password di Figma. Pemilik: Daffaa (`accounts`).

## Alur

1. Di halaman Masuk ada tautan "Lupa password?" ke `/lupa-password/`.
2. Pengguna mengisi email. Halaman berikutnya selalu sama ("Kalau email itu terdaftar, tautan sudah dikirim"), supaya tidak membocorkan akun mana yang ada.
3. Email berisi tautan sekali pakai ke `/lupa-password/<uidb64>/<token>/`. Token kedaluwarsa setelah 1 jam dan tidak berlaku lagi setelah password diganti.
4. Pengguna mengisi password baru dua kali. Validatornya sama dengan pendaftaran (minimal 8 karakter, huruf dan angka).
5. Halaman selesai menaut ke Masuk. Pengguna tidak langsung masuk.

## Implementasi

Semua bagian inti sudah tersedia di Django, jadi tidak ada dependency baru.

| Bagian | Isi |
|--------|-----|
| URL di `accounts/urls.py` | Empat view bawaan: `PasswordResetView`, `PasswordResetDoneView`, `PasswordResetConfirmView`, `PasswordResetCompleteView` |
| Form | Subclass `PasswordResetForm` dan `SetPasswordForm` dengan mixin `Styled`, supaya tampilannya sama dengan form lain |
| Template di `templates/accounts/` | `password_reset_form.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html` memakai `_auth_layout.html`, ditambah `password_reset_email.txt` dan `password_reset_subject.txt` |
| `settings.py` | `PASSWORD_RESET_TIMEOUT = 3600`, `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USE_TLS`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`. Semua nilai rahasia dari environment |
| Lokal | `EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"`, jadi email tampil di terminal |
| PWS | SMTP Gmail dengan app password (akun khusus proyek, bukan akun pribadi), disimpan sebagai environment variable di PWS |
| Figma | Tambah dua layar kecil di frame 12 dan 13: isi email, dan isi password baru |

## Catatan keamanan

- Akun yang dibuat lewat `createsuperuser` dengan email palsu tidak bisa memakai fitur ini. Kurator tetap bisa mengganti password lewat `/admin/`.
- Pendaftaran tidak memverifikasi email, jadi siapa pun bisa mendaftar dengan email orang lain. Reset password mengirim tautan ke pemilik email asli, sehingga pemilik email bisa mengambil alih akun yang didaftarkan atas namanya.
- Permintaan reset tidak dihitung django-axes. Bila disalahgunakan untuk spam email, tambahkan batas per email per jam.

## Tes

- Email terdaftar mengirim satu email berisi tautan (`django.core.mail.outbox`).
- Email tidak terdaftar menampilkan halaman yang sama dan tidak mengirim apa pun.
- Token valid mengganti password, token kedua kali ditolak, token kedaluwarsa ditolak.
- Password baru tanpa angka ditolak.

## Perkiraan

Kode dan tes 2 sampai 3 jam. Pengaturan SMTP dan percobaan di PWS sekitar 1 jam.

## Kalau tidak dikerjakan

Tidak ada yang rusak. Pengguna yang lupa password menghubungi kurator, yang menggantinya lewat `/admin/`.
