# Reset password

Selesai 24 Oktober (4 tes di `accounts/tests.py`). Pemilik: Daffaa (`accounts`). Di laptop email dicetak ke terminal. Di PWS email terkirim lewat SMTP Gmail (app password) sejak 27 Oktober, memakai `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, dan opsional `EMAIL_PORT` dan `DEFAULT_FROM_EMAIL` dari environment. Variabel baru baru berlaku setelah redeploy. Figma frame 12 dan 13 sudah memuat tautan dan layarnya.

## Alur

1. Halaman Masuk punya tautan "Lupa password?" ke `/lupa-password/`.
2. Pengguna mengisi email. Halaman berikutnya selalu sama ("Kalau email itu terdaftar, tautan sudah dikirim"), sehingga akun tidak bisa ditebak.
3. Email berisi tautan sekali pakai ke `/lupa-password/<uidb64>/<token>/`. Token kedaluwarsa setelah 1 jam dan gugur setelah password diganti.
4. Pengguna mengisi password baru dua kali dengan validator yang sama dengan pendaftaran (minimal 8 karakter, huruf dan angka).
5. Halaman selesai menaut ke Masuk. Pengguna tidak langsung masuk.

## Implementasi

Memakai view dan form bawaan Django, tanpa dependency baru.

| Bagian | Isi |
|--------|-----|
| `accounts/urls.py` | `PasswordResetView`, `PasswordResetDoneView`, `PasswordResetConfirmView`, `PasswordResetCompleteView` |
| Form | Subclass `PasswordResetForm` dan `SetPasswordForm` dengan mixin `Styled` |
| `templates/accounts/` | `password_reset_form.html`, `_done.html`, `_confirm.html`, `_complete.html` (memakai `_auth_layout.html`), `password_reset_email.txt`, `password_reset_subject.txt` |
| `settings.py` | `PASSWORD_RESET_TIMEOUT = 3600` dan pengaturan email. Nilai rahasia dari environment, dan backend console di lokal |

## Catatan keamanan

- Akun dari `createsuperuser` dengan email palsu tidak bisa memakai fitur ini. Kurator tetap bisa mengganti password lewat `/admin/`.
- Pendaftaran belum memverifikasi email, jadi pemilik email asli bisa mengambil alih akun yang didaftarkan atas namanya lewat reset.
- Permintaan reset tidak dihitung django-axes. Bila disalahgunakan untuk spam, tambahkan batas per email per jam.

## Tes

Email terdaftar mengirim satu email berisi tautan, email tak terdaftar menampilkan halaman yang sama tanpa mengirim apa pun, token valid mengganti password (pemakaian kedua dan token kedaluwarsa ditolak), dan password baru tanpa angka ditolak.
