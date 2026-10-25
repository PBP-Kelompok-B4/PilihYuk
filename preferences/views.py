from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from .constants import DEFAULT_DIRECTION, DEFAULT_WEIGHT, DIRECTION_CHOICES, NUTRIENT_FIELDS, WEIGHT_CHOICES
from .decorators import owner_required
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


@login_required
@require_GET
def preference_list(request):
    return render(request, "preferences/preference_list.html", preference_context(request.user))


@login_required
@require_POST
def preference_create(request):
    form = PreferenceForm(request.POST, user=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, "Preferensi disimpan.")
        return redirect("preferences:preference_list")
    return render(request, "preferences/preference_list.html", preference_context(request.user, form), status=400)


@login_required
@require_POST
@owner_required(Preference)
def preference_update(request, item):
    form = PreferenceForm(request.POST, user=request.user, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, "Preferensi disimpan.")
        return redirect("preferences:preference_list")
    return render(request, "preferences/preference_list.html", preference_context(request.user, form), status=400)


@login_required
@require_POST
@owner_required(Preference)
def preference_delete(request, item):
    item.delete()
    messages.success(request, "Preferensi dihapus.")
    return redirect("preferences:preference_list")
