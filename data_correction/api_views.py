"""API DRF Modul Antrean Data. Aturan tetap di services, validators, dan contribution."""
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from product_catalog.models import Product

from . import contribution, services, shelf_frequency
from .forms import GROUPS, CorrectionForm
from .models import DataCorrection
from .serializers import (
    ContributionQueueSerializer,
    CorrectionFormSerializer,
    CorrectionPageSerializer,
    CorrectionSerializer,
    CorrectionSubmitSerializer,
)
from .services import CorrectionError
from .validators import to_display
from .views import CONTRIBUTION_PAGE_SIZE, PAGE_SIZE

INVALID_MESSAGE = "Periksa kembali isian koreksi."
GROUP_TITLES = {name: title for title, names in GROUPS for name in names}


def error_body(error):
    """CorrectionError -> {"detail", "code", "fields"?}."""
    body = {"detail": error.message, "code": error.error_id}
    if error.fields:
        body["fields"] = {
            str(name): [str(message) for message in messages] for name, messages in error.fields.items()
        }
    return body


def correction_errors(view):
    """Ubah CorrectionError menjadi Response galat modul."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except CorrectionError as error:
            return Response(error_body(error), status=error.status)

    return wrapped


def shape_errors(errors):
    """Galat serializer -> {kunci: [pesan]}, mis. {"items": ["Baris 2, field_name: ..."]}."""
    return {str(name): _messages(value) for name, value in errors.items()}


def _messages(value, where=""):
    if isinstance(value, dict):
        messages = []
        for key, inner in value.items():
            if key == "non_field_errors":
                messages += _messages(inner, where)
            elif isinstance(key, int):
                messages += _messages(inner, f"{where}Baris {key + 1}, ")
            else:
                messages += _messages(inner, f"{where}{key}: ")
        return messages
    if isinstance(value, list):
        return [message for inner in value for message in _messages(inner, where)]
    return [f"{where}{value}"]


def active_product(pk):
    try:
        return get_object_or_404(Product, pk=pk, is_active=True)
    except Http404:
        raise CorrectionError("product_not_found", "Produk tidak ditemukan.", 404) from None


def page_fields(page):
    return {
        "count": page.paginator.count,
        "page": page.number,
        "page_size": page.paginator.per_page,
        "num_pages": page.paginator.num_pages,
        "next_page": page.next_page_number() if page.has_next() else None,
        "previous_page": page.previous_page_number() if page.has_previous() else None,
    }


def own_corrections(user):
    """Sama dengan queryset views.my_corrections."""
    return (
        DataCorrection.objects.filter(submitted_by=user)
        .select_related("product")
        .prefetch_related("items")
        .order_by("-created_at", "-pk")
    )


def own_correction(user, pk):
    """Milik orang lain dijawab 404, sama dengan yang tidak ada."""
    try:
        return get_object_or_404(own_corrections(user), pk=pk)
    except Http404:
        raise CorrectionError("correction_not_found", "Pengajuan tidak ditemukan.", 404) from None


def contribution_queue_data(query):
    frequency = shelf_frequency.shelf_counts()
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
    """GET queue/?sort=&missing=&page= (publik)."""
    return Response(ContributionQueueSerializer(contribution_queue_data(request.query_params)).data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@correction_errors
def correction_form(request, pk):
    """GET products/<pk>/form/?field=<nama> (boleh berulang)."""
    product = active_product(pk)
    form = CorrectionForm(None, product=product, focus=request.query_params.getlist("field"))
    fields = [
        {
            **field,
            "group": GROUP_TITLES[field["field_name"]],
            "current_display": to_display(field["field_name"], field["current_value"]),
        }
        for field in form.json_fields()
    ]
    data = {"product": product, "focus": form.focus, "correctable_fields": fields}
    return Response(CorrectionFormSerializer(data).data)


@api_view(["GET", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@correction_errors
def my_corrections(request):
    """GET mine/?page= daftar milik sendiri; POST mine/ {"product", "items"} ajukan koreksi."""
    if request.method == "GET":
        page = Paginator(own_corrections(request.user), PAGE_SIZE).get_page(request.query_params.get("page"))
        return Response(CorrectionPageSerializer({**page_fields(page), "results": page.object_list}).data)

    body = CorrectionSubmitSerializer(data=request.data)
    if not body.is_valid():
        raise CorrectionError("validation_error", INVALID_MESSAGE, fields=shape_errors(body.errors))
    product = active_product(body.validated_data["product"])
    changes = [(item["field_name"], item["proposed_value"]) for item in body.validated_data["items"]]
    correction = services.submit_correction(request.user, product, changes)
    prefetch_related_objects([correction], "items")
    return Response(CorrectionSerializer(correction).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
@correction_errors
def correction_detail(request, pk):
    """GET mine/<pk>/."""
    return Response(CorrectionSerializer(own_correction(request.user, pk)).data)