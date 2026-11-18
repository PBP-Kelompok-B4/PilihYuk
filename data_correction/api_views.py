"""API Django REST Framework Modul Antrean Data untuk aplikasi Flutter.

Notes:
- Pola mengikuti accounts/api_views.py dan konvensi API di .ai/timeline.md: @api_view,
  @authentication_classes([SessionAuthentication]), @permission_classes, tanpa @csrf_exempt.
  SessionAuthentication hanya memeriksa token CSRF untuk metode yang mengubah data, jadi GET
  dari pbp_django_auth (yang tidak mengirim token CSRF) tetap lolos.
- Aturan TIDAK ditulis ulang di sini. View memanggil fungsi yang sama dengan halaman /antrean/:
  contribution.py (filter, urutan, status, statistik), incomplete.py (lewat queue_products),
  dan shelf_frequency.py. Jadi antrean di aplikasi selalu sama dengan antrean di situs web.
- Identitas pengaju tidak pernah dikirim (F-4.9). Serializer-nya pun tidak punya field itu.
- Daftar endpoint modul ini (termasuk rancangan tahap akhir) ada di api_urls.py.
"""
from django.core.paginator import Paginator
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import contribution, shelf_frequency
from .serializers import ContributionQueueSerializer
from .views import CONTRIBUTION_PAGE_SIZE  # 20, sama dengan halaman web


def contribution_queue_data(query):
    """Satu halaman antrean kontribusi sebagai dict untuk ContributionQueueSerializer.
    Langkahnya sama dengan views.contribution_queue, dengan jumlah query tetap
    (6, atau 7 untuk ?sort=terbaru) berapa pun jumlah produknya.

    Argumen:
        query : request.query_params (?sort=, ?missing=, ?page=)

    Contoh (data seed + data demo):
        contribution_queue_data({"missing": "nova", "page": "2"})
            -> {"count": 186, "page": 2, "page_size": 20, "num_pages": 10, "next_page": 3,
                "previous_page": 1, "sort": "shelf", "missing": "nova", ...}
    """
    frequency = shelf_frequency.shelf_counts()  # satu query untuk semua produk
    filters = contribution.ContributionFilters.from_query(query, frequency.available)
    queue = contribution.queue_products(filters, frequency)
    page = Paginator(queue.rows, CONTRIBUTION_PAGE_SIZE).get_page(filters.page)
    product_ids = [row["pk"] for row in page]
    pending = contribution.pending_product_ids(product_ids)
    images = contribution.page_images(product_ids)
    return {
        "count": page.paginator.count,
        "page": page.number,
        "page_size": page.paginator.per_page,
        "num_pages": page.paginator.num_pages,
        "next_page": page.next_page_number() if page.has_next() else None,
        "previous_page": page.previous_page_number() if page.has_previous() else None,
        "sort": filters.sort,
        "missing": filters.missing or None,
        "shelf_available": frequency.available,
        "sort_options": [{"key": key, "label": label} for key, label in filters.sorts],
        "missing_options": [
            {"key": key, "label": contribution.CATEGORY_LABELS[key]} for key in queue.categories
        ],
        "stats": contribution.contribution_stats(queue.total, queue.shelf_total),
        "results": [contribution.decorate(row, pending, images) for row in page],
    }


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def contribution_queue(request):
    """Antrean kontribusi: produk aktif yang datanya belum lengkap (PRD F-4.7). PUBLIK.

    Query string (sama dengan /antrean/; nilai tidak dikenal kembali ke bawaan):
        ?sort=shelf (bawaan) | kosong | terbaru   tanpa data shelf, bawaannya kosong
        ?missing=<key kategori>                   mis. nutrition, nova, brand, quantity, origin
        ?page=<n>                                 20 produk per halaman; bukan angka -> 1,
                                                  lewat dari halaman terakhir -> terakhir

    Contoh:
        GET /api/v1/corrections/queue/
        GET /api/v1/corrections/queue/?missing=nova&sort=terbaru&page=2
        POST /api/v1/corrections/queue/  -> 405 (sudah login tanpa token CSRF: 403)
    """
    return Response(ContributionQueueSerializer(contribution_queue_data(request.query_params)).data)