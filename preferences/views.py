from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.db import transaction
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse

from product_catalog.models import Product

from .constants import DEFAULT_DIRECTION, DEFAULT_WEIGHT, DIRECTION_CHOICES, NUTRIENT_FIELDS, WEIGHT_CHOICES
from .decorators import module_methods, owner_required, rate_limit, wants_json
from .forms import DecisionBulkDeleteForm, DecisionFilterForm, DecisionForm, PreferenceForm
from .models import Decision, Preference


def preference_context(user, form=None):
    saved = {item.nutrient: item for item in Preference.objects.filter(user=user)}
    rows = []
    for nutrient, metadata in NUTRIENT_FIELDS.items():
        item = saved.get(nutrient)
        rows.append({"nutrient": nutrient, "label": metadata["label"], "item": item,
                     "active": item is not None, "direction": item.direction if item else DEFAULT_DIRECTION,
                     "weight": item.weight if item else DEFAULT_WEIGHT})
    return {"rows": rows, "form": form, "weight_choices": WEIGHT_CHOICES, "direction_choices": DIRECTION_CHOICES}


def preference_item(item):
    return {"id": item.pk, "nutrient": item.nutrient, "nutrient_label": item.get_nutrient_display(),
            "direction": item.direction, "weight": item.weight}


def preference_result(request, item, message, *, status=200):
    if wants_json(request):
        context = preference_context(request.user)
        context["row"] = next(row for row in context["rows"] if row["nutrient"] == item.nutrient)
        html = render_to_string("preferences/_preference_row.html", context, request=request)
        return JsonResponse({"ok": True, "message": message, "item": preference_item(item), "html": html}, status=status)
    messages.success(request, message)
    return redirect("preferences:preference_list")


def preference_invalid(request, form):
    if wants_json(request):
        return JsonResponse({"ok": False, "message": "Periksa kembali isian.", "errors": form.errors}, status=400)
    return render(request, "preferences/preference_list.html", preference_context(request.user, form), status=400)


@login_required
@module_methods("GET")
def preference_list(request):
    if wants_json(request):
        return JsonResponse({"ok": True, "items": [preference_item(item) for item in Preference.objects.filter(user=request.user)]})
    return render(request, "preferences/preference_list.html", preference_context(request.user))


@login_required
@module_methods("POST")
@rate_limit
def preference_create(request):
    form = PreferenceForm(request.POST, user=request.user)
    if form.is_valid():
        return preference_result(request, form.save(), "Preferensi disimpan.", status=201)
    return preference_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Preference)
@rate_limit
def preference_update(request, item):
    form = PreferenceForm(request.POST, user=request.user, instance=item)
    if form.is_valid():
        return preference_result(request, form.save(), "Preferensi disimpan.")
    return preference_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Preference)
@rate_limit
def preference_delete(request, item):
    item_id = item.pk
    item.delete()
    item.pk = item_id
    return preference_result(request, item, "Preferensi dihapus.")


@login_required
@module_methods("GET")
def preference_preview(request):
    nutrient = request.GET.get("nutrient")
    direction = request.GET.get("direction")
    if nutrient not in NUTRIENT_FIELDS or direction not in dict(DIRECTION_CHOICES):
        return JsonResponse({"ok": False, "message": "Nutrien atau arah tidak valid."}, status=400)
    metadata = NUTRIENT_FIELDS[nutrient]
    field = metadata["field"]
    active = Product.objects.filter(is_active=True)
    ranked = active.filter(**{f"{field}__isnull": False})
    ordered = ranked.order_by(("-" if direction == "max" else "") + field, "pk")[:3]
    samples = [{"name": item.product_name, "value": round(getattr(item, field) * metadata["scale"], 1),
                "unit": metadata["unit"]} for item in ordered]
    return JsonResponse({"ok": True, "ranked_count": ranked.count(), "total_active": active.count(), "samples": samples})


def decision_item(item):
    product = Product.objects.filter(pk=item.product_id, is_active=True).first()
    return {"id": item.pk, "product_id": item.product_id,
            "product_name": product.product_name if product else "Tidak diketahui",
            "shelf_id": item.shelf_id, "shelf_name": item.shelf.name if item.shelf else "Tidak diketahui",
            "note": item.note, "created_at": item.created_at.isoformat()}


def decision_context(request, form=None):
    queryset = Decision.objects.filter(user=request.user).select_related("shelf").order_by("-created_at", "-pk")
    filters = DecisionFilterForm(request.GET, user=request.user)
    filters.is_valid()
    data = filters.cleaned_data
    if data.get("q"):
        queryset = queryset.filter(Q(product__product_name__icontains=data["q"]) | Q(product__brand__icontains=data["q"]),
                                   product__is_active=True)
    if data.get("shelf"):
        queryset = queryset.filter(shelf=data["shelf"])
    if data.get("dari"):
        queryset = queryset.filter(created_at__date__gte=data["dari"])
    if data.get("sampai"):
        queryset = queryset.filter(created_at__date__lte=data["sampai"])
    notices = [f"Filter {filters.fields[key].label.lower()} tidak valid dan diabaikan." for key in filters.errors]
    page = Paginator(queryset, 10).get_page(request.GET.get("page"))
    rows = [{"item": decision_item(item), "created_at": item.created_at} for item in page]
    params = request.GET.copy()
    params["page"] = page.number
    current_url = reverse("preferences:decision_list") + "?" + params.urlencode()
    links = {}
    for key, number in (("previous_url", page.number - 1), ("next_url", page.number + 1)):
        params["page"] = number
        links[key] = "?" + params.urlencode()
    return {"rows": rows, "page_obj": page, "form": form if form is not None else DecisionForm(user=request.user),
            "filter_form": filters, "notices": notices, "current_url": current_url, **links}


@login_required
@module_methods("GET")
def decision_list(request):
    context = decision_context(request)
    if wants_json(request):
        html = render_to_string("preferences/_decision_results.html", context, request=request)
        page = context["page_obj"]
        return JsonResponse({"ok": True, "items": [row["item"] for row in context["rows"]],
                             "page": page.number, "pages": page.paginator.num_pages, "total": page.paginator.count,
                             "notices": context["notices"], "url": context["current_url"], "html": html})
    return render(request, "preferences/decision_list.html", context)


def decision_result(request, item, message, *, status=200):
    if wants_json(request):
        return JsonResponse({"ok": True, "message": message, "item": decision_item(item)}, status=status)
    messages.success(request, message)
    return redirect("preferences:decision_list")


def decision_invalid(request, form):
    if wants_json(request):
        return JsonResponse({"ok": False, "message": "Periksa kembali isian.", "errors": form.errors}, status=400)
    context = decision_context(request, form if not form.instance.pk else None)
    context["errors"] = form.errors
    return render(request, "preferences/decision_list.html", context, status=400)


@login_required
@module_methods("POST")
@rate_limit
def decision_create(request):
    form = DecisionForm(request.POST, user=request.user)
    if form.is_valid():
        return decision_result(request, form.save(), "Keputusan disimpan.", status=201)
    return decision_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Decision)
@rate_limit
def decision_update(request, item):
    form = DecisionForm(request.POST, user=request.user, instance=item)
    if form.is_valid():
        return decision_result(request, form.save(), "Alasan disimpan.")
    return decision_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Decision)
@rate_limit
def decision_delete(request, item):
    result = decision_item(item)
    item.delete()
    if wants_json(request):
        return JsonResponse({"ok": True, "message": "Keputusan dihapus.", "item": result})
    messages.success(request, "Keputusan dihapus.")
    return redirect("preferences:decision_list")


def error_response(request, message, status, errors=None):
    if wants_json(request):
        data = {"ok": False, "message": message}
        if errors:
            data["errors"] = errors
        return JsonResponse(data, status=status)
    return render(request, "preferences/_error.html", {"title": "Perubahan tidak tersimpan", "message": message,
                                                       "errors": errors}, status=status)


@login_required
@module_methods("POST")
@rate_limit
def decision_bulk_delete(request):
    form = DecisionBulkDeleteForm(request.POST)
    if not form.is_valid():
        return error_response(request, "Periksa kembali pilihan keputusan.", 400, form.errors)
    ids = form.cleaned_data["ids"]
    with transaction.atomic():
        items = list(Decision.objects.select_for_update().filter(pk__in=ids))
        if any(item.user_id != request.user.pk for item in items):
            return error_response(request, "Kamu tidak punya akses ke data ini.", 403)
        if len(items) != len(ids):
            return error_response(request, "Data tidak ditemukan.", 404)
        Decision.objects.filter(user=request.user, pk__in=ids).delete()
    message = f"{len(ids)} keputusan dihapus."
    if wants_json(request):
        return JsonResponse({"ok": True, "message": message, "deleted_ids": ids})
    messages.success(request, message)
    return redirect("preferences:decision_list")
