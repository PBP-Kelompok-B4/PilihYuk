from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ShelfForm
from .models import Shelf

PAGE_SIZE = 12


def wants_json(request):
    return request.GET.get("format") == "json" or "application/json" in request.headers.get("Accept", "")


def owner_name(user):
    # Email adalah username, jadi jangan pernah ditampilkan ke orang lain.
    return user.first_name or "Pengguna PilihYuk"


def shelves_with_counts():
    return (Shelf.objects.select_related("owner")
            .annotate(item_count=Count("items", distinct=True), save_count=Count("saves", distinct=True))
            .prefetch_related("items__product"))


def serialize_shelf(shelf):
    return {
        "id": shelf.pk,
        "name": shelf.name,
        "store_context": shelf.store_context,
        "description": shelf.description,
        "is_private": shelf.is_private,
        "owner": owner_name(shelf.owner),
        "item_count": shelf.item_count,
        "save_count": shelf.save_count,
        "url": reverse("shelves:detail", args=[shelf.pk]),
        "updated_at": shelf.updated_at.isoformat(),
    }


def paginate(request, queryset, param="page"):
    return Paginator(queryset, PAGE_SIZE).get_page(request.GET.get(param))


def shelf_list(request):
    query = request.GET.get("q", "").strip()
    shelves = shelves_with_counts().filter(is_private=False)
    if query:
        shelves = shelves.filter(Q(name__icontains=query) | Q(store_context__icontains=query)
                                 | Q(description__icontains=query))
    page = paginate(request, shelves)
    if wants_json(request):
        return JsonResponse({"results": [serialize_shelf(s) for s in page], "page": page.number,
                             "num_pages": page.paginator.num_pages, "count": page.paginator.count})
    return render(request, "shelves/list.html", {"page": page, "query": query})


@login_required
def shelf_mine(request):
    shelves = shelves_with_counts()
    own = paginate(request, shelves.filter(owner=request.user))
    saved = paginate(request, shelves.filter(saves__user=request.user, is_private=False)
                     .exclude(owner=request.user), "saved_page")
    return render(request, "shelves/mine.html", {"own": own, "saved": saved})


def shelf_detail(request, pk):
    shelf = get_object_or_404(shelves_with_counts(), pk=pk)
    if shelf.is_private and shelf.owner_id != request.user.pk:
        raise Http404  # 404, bukan 403, supaya orang lain tidak tahu shelf ini ada
    items = shelf.items.select_related("product").filter(product__is_active=True)
    if wants_json(request):
        return JsonResponse({**serialize_shelf(shelf),
                             "products": [{"id": i.product_id, "name": i.product.product_name} for i in items]})
    return render(request, "shelves/detail.html", {
        "shelf": shelf, "items": items, "is_owner": shelf.owner_id == request.user.pk,
        "owner_name": owner_name(shelf.owner),
    })


@login_required
def shelf_create(request):
    form = ShelfForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        shelf = form.save(commit=False)
        shelf.owner = request.user
        shelf.save()
        messages.success(request, "Shelf dibuat. Tambahkan produk untuk mulai membandingkan.")
        return redirect("shelves:detail", pk=shelf.pk)
    return render(request, "shelves/form.html", {"form": form})


@login_required
def shelf_edit(request, pk):
    shelf = get_object_or_404(Shelf, pk=pk, owner=request.user)
    form = ShelfForm(request.POST or None, instance=shelf)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perubahan shelf disimpan.")
        return redirect("shelves:detail", pk=shelf.pk)
    return render(request, "shelves/form.html", {"form": form, "shelf": shelf})


@login_required
@require_POST
def shelf_delete(request, pk):
    shelf = get_object_or_404(Shelf, pk=pk, owner=request.user)
    shelf.delete()
    messages.success(request, f"Shelf \"{shelf.name}\" dihapus.")
    return redirect("shelves:mine")
