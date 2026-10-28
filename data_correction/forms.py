"""Form pengajuan koreksi Modul 4 (Antrean Data).

Notes:
- SATU form berisi satu kotak isian untuk SETIAP field di
  CORRECTABLE_FIELDS (14 kotak, dikelompokkan seperti halaman produk). Kotak yang
  dibiarkan kosong berarti "tidak diubah", jadi satu pengajuan bisa berisi satu field
  atau beberapa field sekaligus.
- Form ini TIDAK memvalidasi nilai. Semua aturan (format angka, natrium dalam mg, batas
  wajar, NOVA 1-4, panjang teks, "sama dengan nilai saat ini") ada di
  validators.parse_proposed_value dan dijalankan oleh services.submit_correction,
  sama untuk HTML maupun JSON. Kesalahan dari service dipasang kembali ke form lewat
  add_correction_error().
- Semua kotak memakai CharField (teks mentah), BUKAN FloatField/IntegerField, supaya
  "7,5" dan "7.5" sama-sama sampai ke validator dengan pesan error yang seragam. Karena
  itu input memakai type="text" + inputmode, bukan type="number".
- Satu-satunya pemeriksaan bawaan Django yang tetap berjalan adalah larangan karakter
  NUL (kode 0) dari CharField. PostgreSQL tidak bisa menyimpan karakter itu, jadi
  changes() berhenti lebih dulu kalau pemeriksaan ini gagal.

Daftar isi:
- help_text_for  : teks bantuan per field (satuan, contoh, "tanpa pemisah ribuan").
- CorrectionForm : changes(), add_correction_error(), groups(), json_fields().
- ReviewForm     : isian tinjau kurator (action approve/reject + review_note).
"""
from django import forms

from product_catalog.models import Product

from .constants import (
    CORRECTABLE_FIELDS,
    DISPLAY_FACTORS,
    FIELD_LABELS,
    INTEGER_FIELDS,
    NUTRITION_FIELDS,
    TEXT_FIELDS,
)
from .services import CorrectionError
from .validators import DISPLAY_UNITS, NOVA_MAX, NOVA_MIN, get_current_value, to_column_value


INPUT_CLASS = (
    "w-full rounded-[10px] bg-white px-4 py-3 text-sm ring-1 ring-line placeholder:text-muted "
    "focus:outline-none focus:ring-2 focus:ring-brand aria-[invalid=true]:ring-[#b42318]"
)

GROUPS = (
    ("Info produk", TEXT_FIELDS),
    ("Tingkat pemrosesan", INTEGER_FIELDS),
    ("Gizi per 100 g", NUTRITION_FIELDS),
)

NUMBER_EXAMPLES = {"energy_kcal_100g": "250", "sodium_100g": "780"}

# Kunci POST yang bukan isian koreksi dan selalu dilewati.
IGNORED_KEYS = ("csrfmiddlewaretoken",)


def help_text_for(field_name):
    """Teks bantuan di bawah kotak isian. Angka batas diambil dari sumber aslinya
    (model Product dan validators.py), tidak ditulis ulang.

    Contoh:
        "brand"          -> "Maksimal 255 karakter."
        "nova_group"     -> "Bilangan bulat 1 sampai 4: 1 = tidak/minim diproses, 4 = ultra-proses."
        "fat_100g"       -> "Angka dalam g per 100 g, tanpa pemisah ribuan. Contoh: 7,5."
        "sodium_100g"    -> "Angka dalam mg per 100 g, tanpa pemisah ribuan. Contoh: 780."
    """
    if field_name in TEXT_FIELDS:
        return f"Maksimal {Product._meta.get_field(field_name).max_length} karakter."
    if field_name in INTEGER_FIELDS:
        return (
            f"Bilangan bulat {NOVA_MIN} sampai {NOVA_MAX}: "
            f"{NOVA_MIN} = tidak/minim diproses, {NOVA_MAX} = ultra-proses."
        )
    unit = DISPLAY_UNITS.get(field_name, "g")
    example = NUMBER_EXAMPLES.get(field_name, "7,5")
    return f"Angka dalam {unit} per 100 g, tanpa pemisah ribuan. Contoh: {example}."


def _widget(field_name):
    """Kotak teks biasa. Keyboard ponsel diatur lewat inputmode, bukan type="number".

    Contoh atribut:
        "brand"        -> maxlength="255" (dari model Product)
        "nova_group"   -> inputmode="numeric"
        "fat_100g"     -> inputmode="decimal"
    """
    attrs = {"class": INPUT_CLASS, "autocomplete": "off"}
    if field_name in TEXT_FIELDS:
        attrs["maxlength"] = Product._meta.get_field(field_name).max_length
    elif field_name in INTEGER_FIELDS:
        attrs["inputmode"] = "numeric"
    else:
        attrs["inputmode"] = "decimal"
    return forms.TextInput(attrs=attrs)


# ===== 2. Form =====


class CorrectionForm(forms.Form):
    """Satu kotak opsional per field koreksi.

    Argumen:
        data    : request.POST (atau None untuk GET)
        product : Product yang dikoreksi, untuk nilai saat ini
        focus   : nama field dari ?field=... (boleh lebih dari satu). Nama di luar
                  CORRECTABLE_FIELDS diabaikan diam-diam.

    Contoh:
        CorrectionForm(None, product=sarimi, focus=["proteins_100g"])
            -> form kosong; kotak protein ditandai dan mendapat autofocus
        CorrectionForm(request.POST, product=sarimi).changes()
            -> [("proteins_100g", "8,5")]
    """

    def __init__(self, *args, product, focus=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.product = product
        # dict.fromkeys membuang nama ganda tanpa mengubah urutan.
        self.focus = [name for name in dict.fromkeys(focus) if name in CORRECTABLE_FIELDS]
        for name in CORRECTABLE_FIELDS:
            self.fields[name] = forms.CharField(
                label=FIELD_LABELS[name],
                required=False,  # kosong = tidak diubah
                help_text=help_text_for(name),
                widget=_widget(name),
            )
        if self.focus:
            self.fields[self.focus[0]].widget.attrs["autofocus"] = True

    def changes(self):
        """Pasangan (field, isian mentah) untuk services.submit_correction.

        Contoh:
            brand=Sarimi&fat_100g=&csrfmiddlewaretoken=x  -> [("brand", "Sarimi")]
            code=123                                       -> [("code", "123")]
            brand=A&brand=B                                -> [("brand", "A"), ("brand", "B")]
        """
        if not self.is_valid():
            raise CorrectionError("validation_error", "Periksa kembali isian koreksi.", fields=self.errors)
        if hasattr(self.data, "lists"):
            entries = self.data.lists()
        else:
            entries = ((name, [value]) for name, value in self.data.items())
        pairs = []
        for name, values in entries:
            if name in IGNORED_KEYS:
                continue
            if len(values) == 1 and not str(values[0]).strip():
                continue  # kotak kosong = tidak diubah
            pairs.extend((name, value) for value in values)
        return pairs

    def add_correction_error(self, error):
        """Pasang CorrectionError dari service ke form, supaya tampil di template.

        Contoh:
            CorrectionError(..., fields={"nova_group": ["Grup NOVA harus ..."]})
                -> form.errors["nova_group"] == ["Grup NOVA harus ..."]
            CorrectionError(..., fields={"code": ["Field ini tidak boleh dikoreksi."]})
                -> form.non_field_errors() == ["code: Field ini tidak boleh dikoreksi."]
            CorrectionError("validation_error", "Pilih minimal satu field untuk dikoreksi.")
                -> form.non_field_errors() == ["Pilih minimal satu field untuk dikoreksi."]
        """
        if error.fields is self.errors:
            return  # error dari changes(): pesannya memang milik form ini dan sudah terpasang
        if not error.fields:
            self.add_error(None, error.message)
            return
        for name, messages in error.fields.items():
            target = name if name in self.fields else None
            for message in messages:
                self.add_error(target, message if target else f"{name}: {message}")

    def groups(self):
        """Kotak-kotak form per kelompok, siap dipakai template.
        "value" adalah nilai kolom Product saat ini; template mengubahnya menjadi teks
        tampilan dengan filter display_value (natrium dalam mg, kosong "Tidak diketahui").

        Contoh:
            [{"title": "Info produk",
              "rows": [{"field": <BoundField brand>, "value": "Sarimi", "focus": False}, ...]},
             {"title": "Tingkat pemrosesan", "rows": [...]},
             {"title": "Gizi per 100 g", "rows": [...]}]
        """
        return [
            {
                "title": title,
                "rows": [
                    {"field": self[name], "value": getattr(self.product, name), "focus": name in self.focus}
                    for name in names
                ],
            }
            for title, names in GROUPS
        ]

    def json_fields(self):
        """Daftar field koreksi untuk JSON (GET halaman ajukan dengan ?format=json).

        Contoh satu elemen:
            {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "type": "number",
             "current_value": 0.3976, "display_factor": 1000,
             "help_text": "Angka dalam mg per 100 g, tanpa pemisah ribuan. Contoh: 780."}
        """
        return [
            {
                "field_name": name,
                "label": FIELD_LABELS[name],
                "type": "text" if name in TEXT_FIELDS else "integer" if name in INTEGER_FIELDS else "number",
                "current_value": to_column_value(name, get_current_value(self.product, name)),
                "display_factor": DISPLAY_FACTORS.get(name, 1),
                "help_text": self.fields[name].help_text,
            }
            for name in CORRECTABLE_FIELDS
        ]

APPROVE = "approve"
REJECT = "reject"
REVIEW_ACTIONS = ((APPROVE, "Setujui"), (REJECT, "Tolak"))
ACTION_MESSAGE = "Pilih aksi approve atau reject."


class ReviewForm(forms.Form):
    """Isian POST moderasi/item/<pk>/tinjau/: action (approve | reject) dan review_note.

    Contoh:
        ReviewForm({"action": "reject", "review_note": "Tidak sesuai label."}).is_valid()  -> True
        ReviewForm({"action": "hapus"}).errors["action"]  -> ["Pilih aksi approve atau reject."]
    """

    action = forms.ChoiceField(
        choices=REVIEW_ACTIONS,
        error_messages={"required": ACTION_MESSAGE, "invalid_choice": ACTION_MESSAGE},
    )
    review_note = forms.CharField(
        label="Catatan kurator",
        required=False,
        help_text="Wajib diisi saat menolak, opsional saat menyetujui. Catatan terlihat oleh pengaju.",
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
    )