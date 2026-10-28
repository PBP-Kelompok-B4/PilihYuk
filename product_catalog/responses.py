"""Public product representation and authentication for HTML/JSON requests."""
from functools import wraps
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.http import Http404
from django.shortcuts import render


def wants_json(request):
    return request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", "")


def catalog_login_required(view):
    html_view = login_required(view)

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated and wants_json(request):
            return json_error("authentication_required", "Silakan masuk terlebih dahulu.", 401)
        try:
            return html_view(request, *args, **kwargs)
        except Http404:
            if wants_json(request):
                return json_error("product_not_found", "Produk tidak ditemukan.", 404)
            raise
    return wrapped


def error_response(request, error_id, message, status, back_url):
    """JSON untuk klien API, halaman pesan biasa untuk form HTML. Status HTTP tetap sama."""
    if wants_json(request):
        return json_error(error_id, message, status)
    return render(request, "product_catalog/action_error.html", {"message": message, "back_url": back_url}, status=status)


def json_error(error_id, message, status, **extra):
    return JsonResponse({"error": {"id": error_id, "message": message}, **extra}, status=status)


def serialize_product(product, user):
    fields = {field.name: getattr(product, field.name) for field in product._meta.concrete_fields
              if field.name != "added_by"}
    fields["off_url"] = ("https://world.openfoodfacts.org/product/" + quote(product.code, safe="")
                         if product.source == "off" and product.code else None)
    fields["environmental_is_estimated"] = bool(product.environmental_grade_estimated)
    if user.is_authenticated and product.source == "manual":
        fields["added_by"] = product.added_by_id
    return fields
