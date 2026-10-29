from urllib.parse import quote

import requests
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import PROTECT
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BarcodeLookupForm, ManualProductForm, has_valid_gtin
from .lookup import reserve_off_lookup, save_imported_product
from .models import Product, ProductView
from .responses import catalog_login_required, json_error, serialize_product, wants_json
from .off_mapping import product_fields, tag_name
from . import open_food_facts as off
from .name_eligibility import screen_name
from .seed_exclusions import load_seed_exclusions


def lookup_exclusions():
    try:
        return load_seed_exclusions()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DatabaseError("Reviewed OFF exclusions unavailable") from exc


def lookup_result(request, product):
    if not product.is_active:
        if wants_json(request):
            return json_error("product_inactive", "Produk tidak aktif; data tidak diubah.", 409)
        return render(request, "product_catalog/product_lookup.html", {
            "form": BarcodeLookupForm(request.POST),
            "error": "Produk sudah tercatat tetapi tidak aktif; data tidak diubah.",
        }, status=409)
    if product.source == "off" and (off.normalize_barcode(product.code) in lookup_exclusions() or screen_name(product.product_name)[0]):
        message = "Produk Open Food Facts tidak memenuhi kebijakan nama/barcode katalog. Gunakan tambah manual."
        if wants_json(request):
            return json_error("invalid_off_response", message, 422,
                              manual_add_url=reverse("product_catalog:product_add_manual"))
        return render(request, "product_catalog/product_lookup.html", {
            "form": BarcodeLookupForm(request.POST), "error": message,
        }, status=422)
    if wants_json(request):
        return JsonResponse(serialize_product(product, request.user))
    return redirect("product_catalog:product_detail", pk=product.pk)


@transaction.non_atomic_requests
@catalog_login_required
@require_http_methods(["GET", "POST"])
def product_lookup(request):
    form = BarcodeLookupForm(request.POST if request.method == "POST" else None)
    error, status, retry_after, error_id = None, 200, None, None
    if request.method == "POST":
        if not form.is_valid():
            status = 400
        else:
            code = form.cleaned_data["barcode"]
            try:
                existing = Product.objects.filter(code=code).first()
                if existing:
                    return lookup_result(request, existing)
                if code in lookup_exclusions():
                    message = "Barcode ini dikecualikan dari katalog Open Food Facts."
                    if wants_json(request):
                        return json_error("invalid_off_response", message, 422,
                                          manual_add_url=reverse("product_catalog:product_add_manual"))
                    return render(request, "product_catalog/product_lookup.html", {"form": form, "error": message}, status=422)
                retry_after = reserve_off_lookup(request.user)
                if retry_after:
                    error, status = "Batas 3 lookup dalam 60 detik tercapai. Coba lagi nanti.", 429
                else:
                    record = off.fetch_product(code)
                    if record is None:
                        error, status = "Produk tidak ditemukan di Open Food Facts. Anda dapat menambahkannya secara manual.", 404
                    elif not off.is_sold_in_indonesia(record):
                        error, status = "Open Food Facts belum mencatat produk ini dijual di Indonesia. Impor ditolak; tambahkan secara manual jika dijual di Indonesia.", 422
                    else:
                        fields = product_fields(record, tolerate_invalid_nutriscore=True)
                        if screen_name(fields["product_name"])[0]:
                            error, status = "Nama produk Open Food Facts tidak memenuhi kebijakan katalog. Gunakan tambah manual.", 422
                            error_id = "invalid_off_response"
                        else:
                            if fields["code"] != code or not has_valid_gtin(fields["code"]):
                                raise ValueError("OFF returned an inconsistent barcode")
                            return lookup_result(request, save_imported_product(fields, request.user))
            except requests.HTTPError as exc:
                remote_status = exc.response.status_code if exc.response is not None else None
                status = 503 if remote_status == 429 or (remote_status and remote_status >= 500) else 502
                error = "Open Food Facts tidak dapat melayani permintaan. Coba lagi nanti atau tambah manual."
            except requests.RequestException:
                error, status = "Tidak dapat menghubungi Open Food Facts. Coba lagi nanti atau tambah manual.", 503
            except (ValueError, ValidationError):
                error, status = "Data Open Food Facts tidak valid dan tidak disimpan. Anda dapat menambah produk secara manual.", 502
            except DatabaseError:
                error, status = "Penyimpanan sementara tidak tersedia. Lookup dihentikan; coba lagi nanti.", 503
    if wants_json(request):
        ids = {400: "invalid_barcode", 404: "product_not_found", 422: "not_indonesian",
               429: "rate_limited", 502: "invalid_off_response", 503: "service_unavailable"}
        response = (json_error(error_id or ids[status], error or "Barcode tidak valid.", status,
                               fields=form.errors.get_json_data(), manual_add_url=reverse("product_catalog:product_add_manual"))
                    if status != 200 else JsonResponse({"fields": ["barcode"]}))
    else:
        response = render(request, "product_catalog/product_lookup.html", {"form": form, "error": error}, status=status)
    if retry_after:
        response["Retry-After"] = str(retry_after)
    return response


@catalog_login_required
@require_http_methods(["GET", "POST"])
def product_add_manual(request):
    form = ManualProductForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        product = form.save(commit=False)
        product.source, product.added_by, product.code = "manual", request.user, None
        try:
            product.full_clean()
            product.save()
        except DatabaseError:
            if wants_json(request):
                return json_error("storage_unavailable", "Produk belum disimpan. Coba lagi nanti.", 503)
            form.add_error(None, "Produk belum disimpan. Coba lagi nanti.")
            return render(request, "product_catalog/product_manual.html", {"form": form}, status=503)
        if wants_json(request):
            return JsonResponse(serialize_product(product, request.user), status=201)
        return redirect("product_catalog:product_detail", pk=product.pk)
    if wants_json(request):
        if request.method == "POST":
            return json_error("validation_error", "Periksa isian produk yang tidak valid.", 400,
                              fields=form.errors.get_json_data())
        return JsonResponse({"fields": form.errors.get_json_data()})
    return render(request, "product_catalog/product_manual.html", {"form": form})


def product_list(request):
    active = Product.objects.filter(is_active=True)
    products = active
    filters = {key: request.GET.get(key, "").strip() for key in (
        "q", "category", "brand", "origin", "nutrition_grade", "halal",
    )}
    if filters["q"]:
        products = products.filter(
            Q(product_name__icontains=filters["q"]) |
            Q(brand__icontains=filters["q"]) | Q(code__icontains=filters["q"])
        )
    for field in ("category", "brand", "origin", "nutrition_grade"):
        if filters[field]:
            products = products.filter(**{field: filters[field]})
    if filters["halal"] == "1":
        products = products.filter(halal_labeled=True)
    options = {
        field: active.exclude(**{field: ""}).order_by(field).values_list(field, flat=True).distinct()
        for field in ("category", "brand", "origin")
    }
    page = Paginator(products.order_by("product_name", "pk"), 12).get_page(request.GET.get("page"))
    if wants_json(request):
        return JsonResponse({"count": page.paginator.count, "page": page.number, "page_size": 12,
                             "results": [serialize_product(product, request.user) for product in page]})
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "product_catalog/_product_results.html" if request.GET.get("partial") == "1" else "product_catalog/product_list.html", {
        "products": page.object_list, "page_obj": page, "query": query.urlencode(), "filters": filters,
        "options": options, "nutrition_grades": Product.NUTRITION_GRADES,
    })


def product_detail(request, pk):
    product = Product.objects.select_related("added_by").filter(pk=pk, is_active=True).first()
    if product is None:
        if wants_json(request):
            return json_error("product_not_found", "Produk tidak ditemukan.", 404)
        product = get_object_or_404(Product, pk=pk, is_active=True)
    if request.user.is_authenticated:
        ProductView.objects.create(user=request.user, product=product)
    recommendations = product.outgoing_recommendations.annotate(
        agree_count=Count("votes", filter=Q(votes__value=1)),
        disagree_count=Count("votes", filter=Q(votes__value=-1)),
    ).select_related("replacement_product").order_by("-agree_count", "disagree_count", "-created_at")
    for recommendation in recommendations:
        recommendation.score = recommendation.agree_count - recommendation.disagree_count
    if wants_json(request):
        data = serialize_product(product, request.user)
        data["recommendations"] = [
            {
                "id": recommendation.pk,
                "replacement_product": serialize_product(recommendation.replacement_product, request.user),
                "reason": recommendation.reason,
                "agree_count": recommendation.agree_count,
                "disagree_count": recommendation.disagree_count,
                "score": recommendation.score,
                "created_at": recommendation.created_at.isoformat(),
            }
            for recommendation in recommendations
        ]
        return JsonResponse(data)
    nutrient_fields = (
        ("Energi", "energy_kcal_100g", "kkal"),
        ("Protein", "proteins_100g", "g"),
        ("Lemak", "fat_100g", "g"),
        ("Lemak jenuh", "saturated_fat_100g", "g"),
        ("Karbohidrat", "carbohydrates_100g", "g"),
        ("Gula", "sugars_100g", "g"),
        ("Serat", "fiber_100g", "g"),
        ("Natrium", "sodium_100g", "mg"),
    )
    nutrients = []
    for label, field, unit in nutrient_fields:
        value = getattr(product, field)
        if field == "sodium_100g" and value is not None:
            value *= 1000
        nutrients.append({"label": label, "value": value, "unit": unit})
    off_url = None
    if product.source == "off" and product.code:
        off_url = "https://world.openfoodfacts.org/product/" + quote(product.code, safe="")
    return render(request, "product_catalog/product_detail.html", {
        "product": product, "nutrients": nutrients, "off_url": off_url,
        "recommendations": recommendations,
        "packaging": [tag_name(tag) for tag in product.packaging_tags],
        "allergens": [tag_name(tag) for tag in product.allergens],
        "can_edit": request.user.is_authenticated and product.source == "manual" and
                    (request.user.is_staff or product.added_by_id == request.user.pk),
        "can_delete": request.user.is_authenticated and product.source == "manual" and product.added_by_id == request.user.pk,
    })


@catalog_login_required
@require_http_methods(["GET", "POST"])
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if product.source != "manual" or not (request.user.is_staff or product.added_by_id == request.user.pk):
        return json_error("forbidden", "Produk OFF dikoreksi lewat modul Antrean Data; entri manual hanya dapat disunting pemilik atau kurator.", 403)
    form = ManualProductForm(request.POST if request.method == "POST" else None, instance=product)
    if request.method == "POST" and form.is_valid():
        form.save()
        return lookup_result(request, product)
    if wants_json(request):
        if request.method == "POST":
            return json_error("validation_error", "Periksa isian produk yang tidak valid.", 400,
                              product=serialize_product(product, request.user), fields=form.errors.get_json_data())
        return JsonResponse({"product": serialize_product(product, request.user), "fields": form.errors.get_json_data()})
    return render(request, "product_catalog/product_manual.html", {"form": form, "editing": True})


@catalog_login_required
@require_http_methods(["POST"])
def product_delete(request, pk):
    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk, is_active=True)
        if product.source != "manual" or product.added_by_id != request.user.pk:
            return json_error("forbidden", "Hanya pemilik dapat menghapus produk manual.", 403)
        for relation in Product._meta.related_objects:
            if relation.on_delete is PROTECT and relation.related_model.objects.filter(**{relation.field.name: product}).exists():
                return json_error("product_in_use", "Produk masih digunakan dan tidak dapat dihapus.", 409)
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
    if wants_json(request):
        return JsonResponse({"deleted": True, "id": product.pk})
    return redirect("product_catalog:product_list")


@catalog_login_required
def product_history(request):
    page = Paginator(ProductView.objects.filter(user=request.user).select_related("product").order_by("-viewed_at", "-pk"), 12).get_page(request.GET.get("page"))
    if wants_json(request):
        return JsonResponse({"count": page.paginator.count, "page": page.number, "page_size": 12,
                             "results": [{"id": row.pk, "product_id": row.product_id, "viewed_at": row.viewed_at,
                                          "product_name": row.product.product_name, "is_active": row.product.is_active} for row in page]})
    return render(request, "product_catalog/product_history.html", {"page_obj": page})
