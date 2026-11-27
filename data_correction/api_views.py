"""API DRF Modul Antrean Data. Aturan tetap di services, validators, dan contribution."""
from dataclasses import replace
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import prefetch_related_objects
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from product_catalog.models import Product

from . import contribution, moderation, services, shelf_frequency
from .constants import APPROVED, CORRECTABLE_FIELDS, FIELD_LABELS, REJECTED, STATUS_CHOICES
from .forms import APPROVE, GROUPS, REJECT, CorrectionForm, ReviewForm
from .models import DataCorrection
from .permissions import Curator, LoggedIn
from .serializers import (
    ContributionQueueSerializer,
    CorrectionFormSerializer,
    CorrectionPageSerializer,
    CorrectionSerializer,
    CorrectionSubmitSerializer,
    CorrectionUpdateSerializer,
    FieldGuideEntrySerializer,
    ModerationPageSerializer,
    ModerationRowSerializer,
)
from .services import CorrectionError
from .validators import get_current_value, to_column_value, to_display
from .views import CONTRIBUTION_PAGE_SIZE, PAGE_SIZE, QUEUE_PAGE_SIZE, _review_message

INVALID_MESSAGE = "Periksa kembali isian koreksi."
ITEM_NOT_FOUND = "Item tidak ditemukan atau pengajuannya sudah ditarik."
STATUS_MESSAGE = "Pilih status approved atau rejected."
REVIEW_ACTIONS = {APPROVED: APPROVE, REJECTED: REJECT}
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


def body_changes(body):
    """Serializer body POST/PATCH -> [(field_name, proposed_value), ...]; bentuk salah -> 400 validation_error.
    Isinya (field boleh dikoreksi, nilai sah, field ganda) dinilai services, bukan di sini.

    Contoh:
        {"items": [{"field_name": "sodium_100g", "proposed_value": "500"}]}  -> [("sodium_100g", "500")]
        {"items": "brand"}  -> CorrectionError("validation_error", ..., fields={"items": [...]})
    """
    if not body.is_valid():
        raise CorrectionError("validation_error", INVALID_MESSAGE, fields=shape_errors(body.errors))
    return [(item["field_name"], item["proposed_value"]) for item in body.validated_data["items"]]


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


def review_input(data):
    """Body PATCH {"status", "review_note"} -> cleaned_data ReviewForm (action, review_note)."""
    data = data if hasattr(data, "get") else {}
    value = data.get("status")
    action = REVIEW_ACTIONS.get(value) if isinstance(value, str) else None
    if action is None:
        raise CorrectionError("validation_error", STATUS_MESSAGE, fields={"status": [STATUS_MESSAGE]})
    form = ReviewForm({"action": action, "review_note": data.get("review_note") or ""})
    if not form.is_valid():
        raise CorrectionError("validation_error", INVALID_MESSAGE, fields=form.errors)
    return form.cleaned_data


def review_data(result):
    """ReviewResult -> balasan PATCH: serialize_review web, plus baris item lengkap, display, message."""
    item = result.item
    correction, product = item.correction, item.correction.product
    value = get_current_value(product, item.field_name)
    return {
        "item": ModerationRowSerializer(moderation.queue_row(item, moderation.QueueFilters())).data,
        "correction": {
            "id": correction.pk,
            "status": correction.status,
            "status_label": correction.get_status_display(),
        },
        "product": {
            "id": product.pk,
            "field_name": item.field_name,
            "value": to_column_value(item.field_name, value),
            "display": to_display(item.field_name, value),
        },
        "stale": result.stale,
        "message": _review_message(result),
    }


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
@permission_classes([LoggedIn])
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
@permission_classes([LoggedIn])
@correction_errors
def my_corrections(request):
    """GET mine/?page= daftar milik sendiri; POST mine/ {"product", "items"} ajukan koreksi."""
    if request.method == "GET":
        page = Paginator(own_corrections(request.user), PAGE_SIZE).get_page(request.query_params.get("page"))
        return Response(CorrectionPageSerializer({**page_fields(page), "results": page.object_list}).data)

    body = CorrectionSubmitSerializer(data=request.data)
    changes = body_changes(body)
    product = active_product(body.validated_data["product"])
    correction = services.submit_correction(request.user, product, changes)
    prefetch_related_objects([correction], "items")
    return Response(CorrectionSerializer(correction).data, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([LoggedIn])
@correction_errors
def correction_detail(request, pk):
    """GET mine/<pk>/ detail; PATCH {"items"} ganti usulan dan DELETE tarik, keduanya selama semua item
    masih pending (200 berisi pengajuan lengkap, 204 tanpa body)."""
    correction = own_correction(request.user, pk)
    if request.method == "PATCH":
        changes = body_changes(CorrectionUpdateSerializer(data=request.data))
        correction = services.update_correction(request.user, correction, changes)
        prefetch_related_objects([correction], "items")
        return Response(CorrectionSerializer(correction).data)
    if request.method == "DELETE":
        services.withdraw_correction(request.user, correction)
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(CorrectionSerializer(correction).data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([LoggedIn, Curator])
def curator_queue(request):
    """GET moderation/?tab=antrean|semua&field=&status=&page= (20 per halaman); tab=panduan -> antrean."""
    filters = moderation.QueueFilters.from_query(request.query_params)
    if filters.tab == "panduan":
        filters = replace(filters, tab=moderation.DEFAULT_TAB)
    page = Paginator(moderation.queue_items(filters), QUEUE_PAGE_SIZE).get_page(filters.page)
    statuses = STATUS_CHOICES if filters.tab == "semua" else ()
    data = {
        **page_fields(page),
        "tab": filters.tab,
        "field": filters.field or None,
        "status": filters.status or None,
        "tab_options": [{"key": key, "label": label} for key, label in moderation.TABS],
        "field_options": [{"key": name, "label": FIELD_LABELS[name]} for name in CORRECTABLE_FIELDS],
        "status_options": [{"key": key, "label": label} for key, label in statuses],
        "stats": moderation.queue_stats(),
        "results": [moderation.queue_row(item, filters) for item in page],
    }
    return Response(ModerationPageSerializer(data).data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([LoggedIn, Curator])
def field_guide(request):
    """GET moderation/guide/ -> {"fields": [...]}, isi tab Panduan field."""
    return Response({"fields": FieldGuideEntrySerializer(moderation.field_guide(), many=True).data})


@api_view(["GET", "PATCH"])
@authentication_classes([SessionAuthentication])
@permission_classes([LoggedIn, Curator])
@correction_errors
def curator_item(request, pk):
    """GET moderation/items/<pk>/ (yang sudah ditinjau tetap bisa dibaca);
    PATCH {"status": "approved"|"rejected", "review_note"} meninjau item lewat services."""
    item = moderation.find_item(pk)
    if item is None:
        raise CorrectionError("correction_not_found", ITEM_NOT_FOUND, 404)
    if request.method == "PATCH":
        review = review_input(request.data)
        review_item = services.approve_item if review["action"] == APPROVE else services.reject_item
        return Response(review_data(review_item(request.user, item, review["review_note"])))
    return Response(ModerationRowSerializer(moderation.queue_row(item, moderation.QueueFilters())).data)


@api_view(["GET"])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def me(request):
    """GET me/ -> {"logged_in", "is_staff"}; sesi kedaluwarsa dibaca sebagai belum masuk."""
    return Response({"logged_in": request.user.is_authenticated, "is_staff": request.user.is_staff})