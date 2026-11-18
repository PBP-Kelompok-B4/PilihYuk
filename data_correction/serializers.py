"""Serializer Django REST Framework Modul Antrean Data untuk aplikasi Flutter.

Notes:
- Semua serializer di sini HANYA untuk keluaran (read-only). Datanya dict yang sudah disusun
  contribution.py, bukan instance model, jadi memakai serializers.Serializer biasa.
- Bentuk satu baris sama dengan ?format=json di /antrean/, tanpa submit_url dan detail_url
  (keduanya tautan halaman web, tidak dipakai aplikasi), ditambah image_url.
- Identitas pengaju TIDAK PERNAH ada di sini (F-4.9): tidak ada field user, nama, atau email.

Daftar isi:
1. MissingEntrySerializer       : satu kategori data yang kurang
2. ContributionRowSerializer    : satu produk di antrean
3. ContributionStatsSerializer  : kartu statistik
4. OptionSerializer             : pilihan urutan dan filter
5. ContributionQueueSerializer  : satu halaman antrean lengkap
"""
from rest_framework import serializers


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