"""Filter template Modul 4 (Antrean Data).

Notes:
- Dimuat di template dengan {% load data_correction_tags %}.
- Isinya hanya pembungkus tipis validators.to_display, supaya aturan tampilan angka
  (natrium dalam mg, koma desimal, paling banyak 3 desimal) tetap di satu tempat.
- Nama berkas sengaja diberi akhiran _tags agar tidak tertukar dengan nama app.
- thousands ada karena django.contrib.humanize tidak dipasang di proyek ini.
"""
from datetime import timedelta

from django import template
from django.utils import timezone
from django.utils.timesince import timesince
from django.utils.formats import number_format

from ..validators import to_display

register = template.Library()

UNKNOWN_LABEL = "Tidak diketahui"


@register.filter
def display_value(value, field_name):
    """Nilai simpanan (old_value/proposed_value) atau nilai kolom Product -> teks tampilan.

    Contoh di template:
        {{ item.proposed_value|display_value:item.field_name }}

    Contoh hasil:
        ("0.78", "sodium_100g")       -> "780"
        (0.3976, "sodium_100g")       -> "397,6"
        ("0", "fiber_100g")           -> "0"
        (None, "fat_100g")            -> "Tidak diketahui"
        ("", "brand")                 -> "Tidak diketahui"
        ("Sarimi", "brand")           -> "Sarimi"
    """
    shown = to_display(field_name, value)
    return UNKNOWN_LABEL if shown is None else shown

@register.filter
def ago(value):
    """Waktu relatif dengan satu satuan saja, seperti di wireframe ("Budi · 2 jam lalu").
    Memakai timesince bawaan Django, jadi satuannya sudah berbahasa Indonesia.

    Contoh hasil (dibanding sekarang):
        20 detik lalu        -> "baru saja"
        2 jam 40 menit lalu  -> "2 jam lalu"
        3 hari 4 jam lalu    -> "3 hari lalu"
        None                 -> ""
    """
    if not value:
        return ""
    if timezone.now() - value < timedelta(minutes=1):
        return "baru saja"
    return f"{timesince(value, depth=1)} lalu"

@register.filter
def is_known(value, field_name):
    """True kalau nilai bisa ditampilkan, False kalau tampilannya "Tidak diketahui".
    Dipakai template untuk memilih antara teks biasa dan chip "Tidak diketahui".

    Contoh hasil:
        (None, "fat_100g")    -> False
        ("", "brand")         -> False
        (0.0, "fiber_100g")   -> True    (nol bukan kosong)
        ("Sarimi", "brand")   -> True
    """
    return to_display(field_name, value) is not None


@register.filter
def thousands(value):
    """Bilangan bulat dengan pemisah ribuan format Indonesia, untuk angka di kartu dan daftar.

    Contoh hasil:
        1248     -> "1.248"
        347      -> "347"
        None     -> "0"
    """
    return number_format(value or 0, decimal_pos=0, force_grouping=True)