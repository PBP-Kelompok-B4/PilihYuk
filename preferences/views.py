from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string

from product_catalog.models import Product

from .constants import DEFAULT_DIRECTION, DEFAULT_WEIGHT, DIRECTION_CHOICES, NUTRIENT_FIELDS, WEIGHT_CHOICES
from .decorators import module_methods, owner_required, wants_json
from .forms import PreferenceForm
from .models import Preference


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
def preference_create(request):
    form = PreferenceForm(request.POST, user=request.user)
    if form.is_valid():
        return preference_result(request, form.save(), "Preferensi disimpan.", status=201)
    return preference_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Preference)
def preference_update(request, item):
    form = PreferenceForm(request.POST, user=request.user, instance=item)
    if form.is_valid():
        return preference_result(request, form.save(), "Preferensi disimpan.")
    return preference_invalid(request, form)


@login_required
@module_methods("POST")
@owner_required(Preference)
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
