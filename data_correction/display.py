"""Display Modul 4 (Antrean Data).

Notes:
- Di proyek ini username berisi email (accounts/forms.py), jadi username TIDAK PERNAH
  ditampilkan. Yang tampil hanya first_name, atau "Pengguna" kalau kosong.
- Aturannya sama dengan display_name di admin.py. admin.py sengaja tidak diubah; kalau
  nanti ingin satu sumber, admin.py cukup mengimpor fungsi dari file ini.
"""

UNKNOWN_USER = "Pengguna"


def display_name(user):
    """Nama yang boleh tampil di halaman.

    Contoh:
        first_name "Budi"   -> "Budi"
        first_name ""       -> "Pengguna"
        None                -> "-"   (mis. akun peninjau sudah dihapus)
    """
    if user is None:
        return "-"
    return (user.first_name or "").strip() or UNKNOWN_USER