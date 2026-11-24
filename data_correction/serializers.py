"""Serializer Django REST Framework Modul Antrean Data untuk aplikasi Flutter.

Notes:
- Serializer KELUARAN hanya membaca. Antrean kontribusi berupa dict dari contribution.py;
  form, pengajuan, dan item berupa instance model.
- Serializer MASUKAN hanya memeriksa BENTUK body (product bilangan bulat, items berupa daftar).
  Aturan isian (field yang boleh dikoreksi, field ganda, format angka, natrium dalam mg) tetap
  di services.submit_correction dan validators.py, tidak ditulis ulang di sini.
- Angka dikirim dalam satuan kolom Product (natrium gram) lewat validators.to_column_value,
  ditambah teks tampilan *_display dari validators.to_display (natrium mg, koma desimal;
  null berarti "Tidak diketahui").
- Bentuk satu baris antrean sama dengan ?format=json di /antrean/, tanpa submit_url dan
  detail_url (keduanya tautan halaman web, tidak dipakai aplikasi), ditambah image_url.
- Identitas pengaju TIDAK PERNAH ada di sini (F-4.9): tidak ada field user, nama, atau email.

Daftar isi:
Antrean kontribusi (queue/)
1. MissingEntrySerializer       : satu kategori data yang kurang
2. ContributionRowSerializer    : satu produk di antrean
3. ContributionStatsSerializer  : kartu statistik
4. OptionSerializer             : pilihan urutan dan filter
5. ContributionQueueSerializer  : satu halaman antrean lengkap
Form dan pengajuan (products/<pk>/form/, mine/)
6. ProductSummarySerializer     : ringkasan produk
7. CorrectionFieldSerializer    : satu field koreksi beserta nilai saat ini
8. CorrectionFormSerializer     : balasan GET form
9. CorrectionItemSerializer     : satu item pengajuan
10. CorrectionSerializer        : satu pengajuan beserta item-nya
11. CorrectionChangeSerializer  : satu baris items di body POST (masukan)
12. CorrectionSubmitSerializer  : body POST mine/ (masukan)
"""
from rest_framework import serializers

from product_catalog.models import Product

from .models import DataCorrection, DataCorrectionItem
from .validators import to_column_value, to_display

# Batas BIGINT. Id yang lebih besar ditolak sebagai galat bentuk sebelum menyentuh database.
MAX_ID = 9223372036854775807


class MissingEntrySerializer(serializers.Serializer):
    """Contoh: {"key": "nutrition", "label": "Gizi", "correctable": true, "fields": ["fiber_100g"]}

    - correctable=false : hanya informasi (mis. "Kemasan"), tidak bisa diisi lewat koreksi;
                          fields-nya kosong.
    """

    key = serializers.CharField()
    label = serializers.CharField()
    correctable = serializers.BooleanField()
    fields = serializers.ListField(child=serializers.CharField())


class ContributionRowSerializer(serializers.Serializer):
    """Satu produk di antrean kontribusi.

    Contoh:
        {"id": 6, "product_name": "Sarimi isi 2 Goreng Ayam Kremes", "brand": "Sarimi Isi 2",
         "quantity": "125g", "image_url": "https://images.openfoodfacts.org/...jpg",
         "missing": [{"key": "nutrition", "label": "Gizi", "correctable": true,
                      "fields": ["fiber_100g"]}],
         "missing_count": 1, "shelf_count": 3,
         "status": "needs_contribution", "status_label": "Perlu kontribusi"}

    - image_url   : "" kalau produk tidak punya gambar
    - shelf_count : jumlah shelf PUBLIK yang memuat produk; null kalau data shelf tidak ada
    - status      : "needs_contribution" atau "needs_verification" (sudah ada usulan menunggu)
    """

    id = serializers.IntegerField(source="pk")
    product_name = serializers.CharField()
    brand = serializers.CharField()
    quantity = serializers.CharField()
    image_url = serializers.CharField()
    missing = MissingEntrySerializer(many=True)
    missing_count = serializers.IntegerField()
    shelf_count = serializers.IntegerField(allow_null=True)
    status = serializers.CharField()
    status_label = serializers.CharField()


class ContributionStatsSerializer(serializers.Serializer):
    """Kartu statistik, dihitung contribution.contribution_stats (semua akun, tanpa filter).

    Contoh: {"incomplete_products": 347, "submitted_last_7_days": 7, "approved": 3,
             "shelf_average": 0.1}
    - shelf_average : null kalau data shelf tidak ada
    """

    incomplete_products = serializers.IntegerField()
    submitted_last_7_days = serializers.IntegerField()
    approved = serializers.IntegerField()
    shelf_average = serializers.FloatField(allow_null=True)


class OptionSerializer(serializers.Serializer):
    """Satu pilihan chip. Contoh: {"key": "terbaru", "label": "Terbaru"}"""

    key = serializers.CharField()
    label = serializers.CharField()


class ContributionQueueSerializer(serializers.Serializer):
    """Satu halaman antrean kontribusi.

    - count, page, page_size, results : bentuk daftar yang sama dengan ?format=json di web
    - num_pages, next_page, previous_page : nomor halaman (null kalau tidak ada)
    - sort, missing : filter yang benar-benar dipakai (nilai tidak dikenal sudah kembali ke
                      bawaan); missing null berarti semua kategori
    - sort_options, missing_options : chip yang bisa ditampilkan aplikasi. sort_options tanpa
                      "shelf" kalau data shelf tidak ada; missing_options hanya kategori yang
                      benar-benar ada di antrean.
    """

    count = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    num_pages = serializers.IntegerField()
    next_page = serializers.IntegerField(allow_null=True)
    previous_page = serializers.IntegerField(allow_null=True)
    sort = serializers.CharField()
    missing = serializers.CharField(allow_null=True)
    shelf_available = serializers.BooleanField()
    sort_options = OptionSerializer(many=True)
    missing_options = OptionSerializer(many=True)
    stats = ContributionStatsSerializer()
    results = ContributionRowSerializer(many=True)


class ProductSummarySerializer(serializers.ModelSerializer):
    """Ringkasan produk di form dan pengajuan.

    Contoh:
        {"id": 7, "product_name": "Sarimi Isi 2 Goreng", "brand": "Sarimi", "quantity": "88 g",
         "image_url": "", "is_active": true}
    - image_url : "" kalau produk tidak punya gambar
    """

    class Meta:
        model = Product
        fields = ("id", "product_name", "brand", "quantity", "image_url", "is_active")
        read_only_fields = fields


class CorrectionFieldSerializer(serializers.Serializer):
    """Satu field koreksi: isi CorrectionForm.json_fields() ditambah group dan current_display.

    Contoh:
        {"field_name": "sodium_100g", "label": "Natrium (mg/100 g)", "group": "Gizi per 100 g",
         "type": "number", "current_value": 0.3976, "current_display": "397,6",
         "display_factor": 1000,
         "help_text": "Angka dalam mg per 100 g, tanpa pemisah ribuan. Contoh: 780."}

    - type            : "text", "integer", atau "number" (aplikasi memilih keyboard dari sini)
    - current_value   : satuan kolom (natrium gram); null kalau tidak diketahui
    - current_display : teks tampilan (natrium mg); null kalau tidak diketahui
    """

    field_name = serializers.CharField()
    label = serializers.CharField()
    group = serializers.CharField()
    type = serializers.CharField()
    current_value = serializers.ReadOnlyField()  # teks, bilangan bulat, desimal, atau null
    current_display = serializers.CharField(allow_null=True)
    display_factor = serializers.IntegerField()
    help_text = serializers.CharField()


class CorrectionFormSerializer(serializers.Serializer):
    """Balasan GET products/<pk>/form/.

    - product            : ringkasan produk
    - focus              : nama field dari ?field= yang dikenal, tanpa ganda (CorrectionForm.focus);
                           aplikasi mengisi baris awal form dari sini
    - correctable_fields : 14 field, urut seperti CORRECTABLE_FIELDS
    """

    product = ProductSummarySerializer()
    focus = serializers.ListField(child=serializers.CharField())
    correctable_fields = CorrectionFieldSerializer(many=True)


class CorrectionItemSerializer(serializers.ModelSerializer):
    """Satu item pengajuan. Kunci sama dengan views.serialize_item, ditambah id dan *_display.

    Contoh:
        {"id": 31, "field_name": "sodium_100g", "label": "Natrium (mg/100 g)",
         "old_value": 0.3976, "proposed_value": 0.78, "old_display": "397,6",
         "proposed_display": "780", "status": "pending", "status_label": "Menunggu",
         "review_note": ""}
    - old_value : nilai produk saat diajukan; null kalau saat itu tidak diketahui
    """

    label = serializers.CharField(source="get_field_name_display")
    old_value = serializers.SerializerMethodField()
    proposed_value = serializers.SerializerMethodField()
    old_display = serializers.SerializerMethodField()
    proposed_display = serializers.SerializerMethodField()
    status_label = serializers.CharField(source="get_status_display")

    class Meta:
        model = DataCorrectionItem
        fields = (
            "id", "field_name", "label", "old_value", "proposed_value", "old_display",
            "proposed_display", "status", "status_label", "review_note",
        )
        read_only_fields = ("id", "field_name", "status", "review_note")

    def get_old_value(self, item):
        return to_column_value(item.field_name, item.old_value)

    def get_proposed_value(self, item):
        return to_column_value(item.field_name, item.proposed_value)

    def get_old_display(self, item):
        return to_display(item.field_name, item.old_value)

    def get_proposed_display(self, item):
        return to_display(item.field_name, item.proposed_value)


class CorrectionSerializer(serializers.ModelSerializer):
    """Satu pengajuan beserta item-nya. Kunci sama dengan views.serialize_correction, tanpa
    detail_url (tautan halaman web) dan dengan ringkasan produk yang lebih lengkap.

    Item sebaiknya sudah di-prefetch (prefetch_related("items") atau prefetch_related_objects),
    karena status, is_withdrawable, dan items sama-sama membaca items.all().

    Contoh:
        {"id": 12, "product": {"id": 7, "product_name": "Sarimi Isi 2 Goreng", ...},
         "status": "pending", "status_label": "Menunggu", "is_withdrawable": true,
         "created_at": "2026-11-24T03:02:10.208586Z", "items": [{...}, {...}]}
    - status : diturunkan dari item (pending, approved, rejected, atau partial)
    """

    product = ProductSummarySerializer()
    status = serializers.CharField()
    status_label = serializers.CharField(source="get_status_display")
    is_withdrawable = serializers.BooleanField()
    items = CorrectionItemSerializer(many=True)

    class Meta:
        model = DataCorrection
        fields = ("id", "product", "status", "status_label", "is_withdrawable", "created_at", "items")
        read_only_fields = ("id", "created_at")


class CorrectionChangeSerializer(serializers.Serializer):
    """Satu baris items di body POST mine/. Hanya bentuk; isinya dinilai validators.py.

    - field_name     : teks. Nama yang tidak boleh dikoreksi ditolak services, bukan di sini.
    - proposed_value : teks atau angka apa adanya (natrium dalam mg), mis. "8,5", "780", 3
    """

    field_name = serializers.CharField()
    proposed_value = serializers.JSONField(allow_null=True)


class CorrectionSubmitSerializer(serializers.Serializer):
    """Bentuk body POST mine/.

    Contoh sah   : {"product": 7, "items": [{"field_name": "proteins_100g", "proposed_value": "8,5"}]}
    Contoh salah : {"items": "brand"} -> product wajib diisi, items harus berupa daftar
    - items kosong lolos di sini; services yang menolaknya ("Pilih minimal satu field ...").
    - Kunci lain di body (mis. submitted_by) diabaikan; pengaju selalu request.user.
    """

    product = serializers.IntegerField(min_value=1, max_value=MAX_ID)
    items = CorrectionChangeSerializer(many=True)