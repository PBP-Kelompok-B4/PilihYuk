"""Filter template Modul 4 (Antrean Data).

Notes:
- Dimuat di template dengan {% load data_correction_tags %}.
- Isinya hanya pembungkus tipis validators.to_display, supaya aturan tampilan angka
  (natrium dalam mg, koma desimal, paling banyak 3 desimal) tetap di satu tempat.
- Nama berkas sengaja diberi akhiran _tags agar tidak tertukar dengan nama app.
"""
from django import template

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