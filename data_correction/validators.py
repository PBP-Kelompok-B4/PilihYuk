"""Validasi dan konversi data correction (Modul 4: Antrean Data).

Notes:
- Memeriksa apakah isian koreksi dari pengguna valud, lalu mengubahnya
  ke tipe kolom Product yang benar (teks, bilangan bulat, atau float).
- Kenapa dipisah dari services.py? Aturan yang sama dipakai DUA KALI:
  1. saat pengguna mengajukan (isian dari form, natrium dalam mg);
  2. saat kurator menyetujui (teks yang sudah tersimpan, natrium sudah dalam gram).
  Karena memakai fungsi yang sama, nilai yang lolos saat diajukan tidak bisa berubah
  arti saat disetujui.
- Aturan satuan:
  - old_value dan proposed_value SELALU disimpan dalam satuan kolom Product
    (natrium dalam gram), sebagai teks desimal yang bersih.
  - Pembagian mg ke gram memakai Decimal, jadi tidak ada ekor float seperti
    "0.7800000000000001".
- Arti "kosong":
  - teks "" dan angka NULL sama-sama disimpan sebagai None ("tidak diketahui");
  - nilai 0 BUKAN kosong.

Daftar fungsi publik (dipakai file lain):
- get_current_value    : nilai Product saat ini -> teks untuk old_value.
- parse_proposed_value : periksa isian usulan -> nilai bertipe kolom, atau pesan error.
- to_stored_text       : nilai bertipe kolom -> teks simpanan (old_value/proposed_value).
- to_column_value      : teks simpanan -> nilai bertipe kolom (untuk JSON).
- to_display           : teks simpanan/nilai kolom -> teks tampilan (untuk template).
Fungsi berawalan garis bawah (_parse_text, _to_decimal, dst.) hanya dipakai di file ini.
"""

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from product_catalog.models import Product

from .constants import (
    CORRECTABLE_FIELDS,
    DISPLAY_FACTORS,
    INTEGER_FIELDS,
    TEXT_FIELDS,
)

# Grup NOVA hanya 1 sampai 4.
NOVA_MIN, NOVA_MAX = 1, 4

# Batas atas wajar per 100 g, untuk menangkap salah ketik (mis. protein 850 g).
DEFAULT_MAX_DISPLAY_VALUE = Decimal(100)  # gizi dalam gram: tidak mungkin > 100 g per 100 g
MAX_DISPLAY_VALUES = {
    "energy_kcal_100g": Decimal(900),     # lemak murni sekitar 900 kkal per 100 g
    "sodium_100g": Decimal(100000),       # 100 g dalam mg
}

# Satuan untuk pesan error, mis. "Nilai maksimal 900 kkal per 100 g".
DISPLAY_UNITS = {"energy_kcal_100g": "kkal", "sodium_100g": "mg"}  # field gizi lain: "g"

# Paling banyak 3 angka di belakang koma (satuan tampilan). Cukup untuk label kemasan,
# sekaligus mencegah teks angka sepanjang apa pun masuk ke proposed_value.
MAX_DECIMAL_PLACES = 3

# Pola angka yang diterima: hanya digit ASCII, satu pemisah desimal (koma ATAU titik),
# boleh diawali tanda +/-.
# Contoh lolos: "7", "7,5", "7.5", ",5", "-1"   Contoh ditolak: "7,5,1", "1e3", "abc"
NUMBER_RE = re.compile(r"[+-]?(?:[0-9]+(?:[.,][0-9]*)?|[.,][0-9]+)")
# Pola bilangan bulat tanpa tanda, untuk NOVA. Contoh lolos: "3"   Ditolak: "2.5", "-1"
INTEGER_RE = re.compile(r"[0-9]+")

# Semua pesan error di satu tempat, agar seragam dan mudah diubah.
MESSAGES = {
    "not_correctable": "Field ini tidak boleh dikoreksi.",
    "required": "Isian ini wajib diisi.",
    "invalid": "Nilai ini tidak valid.",
    "choice": "Pilih salah satu nilai yang tersedia.",
    "nova": "Grup NOVA harus bilangan bulat 1 sampai 4.",
    "number": "Masukkan angka, misalnya 7,5.",
    "separators": "Tulis angka tanpa pemisah ribuan, misalnya 1234,5 (bukan 1.234,5).",
    "negative": "Nilai tidak boleh negatif.",
    "decimals": f"Gunakan paling banyak {MAX_DECIMAL_PLACES} angka di belakang koma.",
    "unchanged": "Usulan sama dengan nilai saat ini.",
}


def get_current_value(product, field_name):
    """Nilai kolom Product saat ini, sebagai teks untuk disimpan di old_value.
    Dipanggil saat pengajuan dibuat, agar kurator bisa melihat nilai lama dan agar bisa
    dideteksi kalau Product sudah berubah sejak diajukan.

    Contoh:
        brand "Sarimi"       -> "Sarimi"
        brand ""             -> None        (teks kosong = tidak diketahui)
        nova_group 3         -> "3"
        sodium_100g 0.3976   -> "0.3976"    (satuan kolom, gram)
        fiber_100g 0.0       -> "0"         (nol bukan kosong)
        proteins_100g None   -> None
        field "code"         -> ValueError  (bukan field koreksi)
    """
    _ensure_correctable(field_name)
    return to_stored_text(field_name, getattr(product, field_name))


def parse_proposed_value(field_name, raw, *, product=None, display_units=True):
    """Periksa satu isian usulan dan ubah ke tipe kolom Product.
    Hasil selalu pasangan (nilai, pesan_error), dan tepat satu yang terisi:
        (nilai, None)    -> isian sah
        (None, "pesan")  -> isian ditolak, pesan siap ditampilkan ke pengguna

    Contoh:
        ("fat_100g", "7,5")                            -> (7.5, None)
        ("fat_100g", "7.5")                            -> (7.5, None)
        ("fat_100g", "0")                              -> (0.0, None)
        ("fat_100g", "-1")                             -> (None, "Nilai tidak boleh negatif.")
        ("sodium_100g", "780")                         -> (0.78, None)   # mg -> g
        ("sodium_100g", "0.78", display_units=False)   -> (0.78, None)   # sudah gram
        ("energy_kcal_100g", "1.234,5")                -> (None, "Tulis angka tanpa pemisah ribuan, ...")
        ("nova_group", "3")                            -> (3, None)
        ("nova_group", "2.5")                          -> (None, "Grup NOVA harus bilangan bulat 1 sampai 4.")
        ("brand", "  Sarimi   Goreng ")                -> ("Sarimi Goreng", None)
        ("brand", "Sarimi", product=<brand "Sarimi">)  -> (None, "Usulan sama dengan nilai saat ini.")
        ("code", "8991234567890")                      -> (None, "Field ini tidak boleh dikoreksi.")
    """
    if field_name not in CORRECTABLE_FIELDS:
        return None, MESSAGES["not_correctable"]

    if field_name in TEXT_FIELDS:
        value, error = _parse_text(field_name, raw)
    elif field_name in INTEGER_FIELDS:
        value, error = _parse_nova(raw)
    else:
        value, error = _parse_nutrient(field_name, raw, display_units)
    if error:
        return None, error

    if product is not None and getattr(product, field_name) == value:
        return None, MESSAGES["unchanged"]
    return value, None


def to_stored_text(field_name, value):
    """Nilai kolom -> teks simpanan (untuk old_value / proposed_value).

    Contoh:
        ("brand", "Sarimi")    -> "Sarimi"
        ("brand", "  ")        -> None
        ("nova_group", 2)      -> "2"
        ("sodium_100g", 0.78)  -> "0.78"   (bukan "0.7800000000000001")
        ("fat_100g", 100.0)    -> "100"
        ("fat_100g", 0.0)      -> "0"
        ("fat_100g", None)     -> None
    """
    if value is None:
        return None
    if field_name in TEXT_FIELDS:
        text = str(value)
        return text if text.strip() else None  # teks kosong/spasi = tidak diketahui
    if field_name in INTEGER_FIELDS:
        return str(int(value))
    # Float: repr() memberi digit terpendek yang tepat, lalu _plain membuang nol berlebih.
    return _plain(Decimal(repr(float(value))))


def to_column_value(field_name, text):
    """Teks simpanan -> nilai kolom, TANPA validasi (untuk JSON dan perbandingan).
    Angka di JSON dikirim dalam satuan kolom, dengan null untuk nilai kosong.

    Contoh:
        ("sodium_100g", "0.3976")  -> 0.3976
        ("nova_group", "3")        -> 3
        ("brand", "Sarimi")        -> "Sarimi"
        ("fat_100g", None)         -> None
    """
    if text is None:
        return None
    if field_name in TEXT_FIELDS:
        return text
    if field_name in INTEGER_FIELDS:
        return int(text)
    return float(text)


def to_display(field_name, value):
    """Teks simpanan atau nilai kolom -> teks tampilan untuk template.
    - Natrium dikali 1000 (gram -> mg).
    - Angka dibulatkan ke paling banyak 3 angka di belakang koma, dengan koma desimal.
    - Sengaja TANPA pemisah ribuan: "1.234" yang disalin balik ke form akan terbaca
      sebagai desimal 1,234.
    - Hasil None berarti tidak diketahui; template menampilkannya "Tidak diketahui".

    Contoh:
        ("sodium_100g", "0.3976")            -> "397,6"
        ("sodium_100g", 0.78)                -> "780"
        ("energy_kcal_100g", "64.70588235")  -> "64,706"
        ("fat_100g", "0")                    -> "0"
        ("nova_group", "3")                  -> "3"
        ("brand", "Sarimi")                  -> "Sarimi"
        ("fat_100g", None)                   -> None
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if field_name in TEXT_FIELDS:
        return str(value)
    if field_name in INTEGER_FIELDS:
        return str(int(value))
    try:
        number = Decimal(value) if isinstance(value, str) else Decimal(repr(float(value)))
        number = number * DISPLAY_FACTORS.get(field_name, 1)  # gram -> mg untuk natrium
        number = number.quantize(Decimal(1).scaleb(-MAX_DECIMAL_PLACES), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        # Teks yang bukan angka (seharusnya tidak terjadi): tampilkan apa adanya.
        return str(value)
    return _plain(number).replace(".", ",")


def _parse_text(field_name, raw):
    """Kolom teks: rapikan spasi, wajib diisi, panjang <= max_length kolom Product.

    Contoh:
        ("brand", " Sarimi\\n Goreng ")  -> ("Sarimi Goreng", None)
        ("brand", "")                   -> (None, "Isian ini wajib diisi.")
        ("quantity", 85)                -> ("85", None)
    """
    if raw is None:
        return None, MESSAGES["required"]
    # Tolak tipe yang tidak masuk akal sebagai teks (mis. list/dict dari JSON, atau True/False).
    if isinstance(raw, bool) or not isinstance(raw, (str, int, float, Decimal)):
        return None, MESSAGES["invalid"]
    # Gabungkan spasi, tab, dan baris baru berlebih menjadi satu spasi.
    text = " ".join(str(raw).split())
    if not text:
        return None, MESSAGES["required"]
    column = Product._meta.get_field(field_name)  # max_length diambil dari model, bukan ditulis ulang
    if column.max_length is not None and len(text) > column.max_length:
        return None, f"Maksimal {column.max_length} karakter (sekarang {len(text)})."
    # Saat ini tidak ada kolom teks yang punya choices (laporan Tahap 0). Penjaga ini
    # mencegah nilai di luar pilihan tersimpan bila suatu hari choices ditambahkan.
    if column.choices and text not in {str(key) for key, _ in column.flatchoices}:
        return None, MESSAGES["choice"]
    return text, None


def _parse_nova(raw):
    """Grup NOVA: bilangan bulat 1 sampai 4.

    Contoh:
        "3" atau 3 atau 3.0                -> (3, None)
        "0", "5", "2.5", "abc", "-1"       -> (None, "Grup NOVA harus bilangan bulat 1 sampai 4.")
        ""                                 -> (None, "Isian ini wajib diisi.")
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, MESSAGES["required"]
    number = None
    if isinstance(raw, bool):
        # True/False secara teknis bilangan bulat di Python, tapi bukan isian yang sah.
        number = None
    elif isinstance(raw, int):
        number = raw
    elif isinstance(raw, (float, Decimal)):
        # Angka dari JSON: 3.0 diterima, 2.5 ditolak.
        exact = Decimal(repr(raw)) if isinstance(raw, float) else raw
        if exact.is_finite() and exact == exact.to_integral_value():
            number = int(exact)
    elif isinstance(raw, str) and INTEGER_RE.fullmatch(raw.strip()):
        number = int(raw.strip())
    if number is None or not NOVA_MIN <= number <= NOVA_MAX:
        return None, MESSAGES["nova"]
    return number, None


def _parse_nutrient(field_name, raw, display_units):
    """Kolom gizi: angka >= 0, di bawah batas wajar, paling banyak 3 desimal.
    Hasilnya float dalam satuan KOLOM (natrium dalam gram).

    Contoh:
        ("fat_100g", "7,5", True)       -> (7.5, None)
        ("sodium_100g", "780", True)    -> (0.78, None)    # isian mg -> disimpan gram
        ("sodium_100g", "0.78", False)  -> (0.78, None)    # sudah gram, tidak dibagi lagi
        ("fat_100g", "100,5", True)     -> (None, "Nilai maksimal 100 g per 100 g.")
    """
    number, error = _to_decimal(raw)
    if error:
        return None, error

    factor = Decimal(DISPLAY_FACTORS.get(field_name, 1))
    shown = number if display_units else number * factor  # nilai dalam satuan tampilan
    if shown < 0:
        return None, MESSAGES["negative"]
    limit = MAX_DISPLAY_VALUES.get(field_name, DEFAULT_MAX_DISPLAY_VALUE)
    if shown > limit:
        unit = DISPLAY_UNITS.get(field_name, "g")
        return None, f"Nilai maksimal {_plain(limit)} {unit} per 100 g."
    if _decimal_places(shown) > MAX_DECIMAL_PLACES:
        return None, MESSAGES["decimals"]

    column = number / factor if display_units else number  # Decimal, tanpa ekor float
    return (0.0 if column == 0 else float(column)), None


def _to_decimal(raw):
    """Isian angka -> Decimal. Koma dan titik sama-sama dianggap pemisah desimal.

    Contoh:
        "7,5"                 -> (Decimal("7.5"), None)
        7.5                   -> (Decimal("7.5"), None)
        "1.234,5"             -> (None, "Tulis angka tanpa pemisah ribuan, ...")
        "abc", "nan", "inf"   -> (None, "Masukkan angka, misalnya 7,5.")
    """
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, MESSAGES["required"]
    if isinstance(raw, bool):
        return None, MESSAGES["number"]
    if isinstance(raw, (int, Decimal)):
        number = Decimal(raw)
    elif isinstance(raw, float):
        number = Decimal(repr(raw))  # repr memberi digit terpendek, mis. 0.78 bukan 0.78000000000000002665
    elif isinstance(raw, str):
        text = raw.strip()
        if "," in text and "." in text:
            return None, MESSAGES["separators"]
        if not NUMBER_RE.fullmatch(text):
            return None, MESSAGES["number"]
        number = Decimal(text.replace(",", "."))
    else:
        return None, MESSAGES["number"]
    # Tolak NaN dan tak hingga.
    if not number.is_finite():
        return None, MESSAGES["number"]
    return number, None


def _plain(number):
    """Decimal -> teks desimal biasa, tanpa notasi eksponen dan tanpa nol berlebih.

    Contoh:
        Decimal("0.780")  -> "0.78"
        Decimal("1E+2")   -> "100"
        Decimal("-0")     -> "0"
    """
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


def _decimal_places(number):
    """Jumlah angka di belakang koma, setelah nol berlebih dibuang.

    Contoh:
        Decimal("7.50")   -> 1
        Decimal("100")    -> 0
        Decimal("0.125")  -> 3
    """
    return max(0, -number.normalize().as_tuple().exponent)


def _ensure_correctable(field_name):
    """Tolak nama field di luar daftar tetap (PRD F-4.2) dengan ValueError.
    Dipakai get_current_value. Berbeda dengan parse_proposed_value yang mengembalikan
    pesan error, fungsi ini melempar exception karena dipanggil oleh kode, bukan isian
    pengguna, jadi nama field yang salah berarti ada bug.

    Contoh:
        "brand"  -> None (lolos)
        "code"   -> ValueError
    """
    if field_name not in CORRECTABLE_FIELDS:
        raise ValueError(f"{field_name!r} bukan field yang boleh dikoreksi.")