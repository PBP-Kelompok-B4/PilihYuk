import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from product_catalog.models import Product

from .comparison import MAX_COMPARED, comparison_rows
from .forms import CandidateSearchForm, ShelfForm, ShelfItemForm
from .models import MAX_SHELF_ITEMS, SavedShelf, Shelf, ShelfItem

PAGE_SIZE = 12
logger = logging.getLogger(__name__)


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


def product_card(product):
    return {"id": product.pk, "name": product.product_name, "brand": product.brand,
            "quantity": product.quantity, "image_url": product.image_url}


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
    products = [i.product for i in shelf.items.select_related("product").filter(product__is_active=True)]
    chosen = request.GET.getlist("banding")
    compared = [p for p in products if str(p.pk) in chosen][:MAX_COMPARED] or products[:MAX_COMPARED]
    rows = comparison_rows(compared)
    is_saved = request.user.is_authenticated and shelf.saves.filter(user=request.user).exists()
    if wants_json(request):
        return JsonResponse({**serialize_shelf(shelf), "products": [product_card(p) for p in products],
                             "compared": [p.pk for p in compared], "rows": rows, "saved": is_saved})
    context = {"shelf": shelf, "products": products, "compared": compared, "rows": rows,
               "max_compared": MAX_COMPARED}
    if request.GET.get("partial"):
        return render(request, "shelves/_comparison.html", context)
    return render(request, "shelves/detail.html", {
        **context, "is_owner": shelf.owner_id == request.user.pk, "owner_name": owner_name(shelf.owner),
        "is_saved": is_saved,
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
    return render(request, "shelves/form.html", {
        "form": form, "shelf": shelf, "items": shelf.items.select_related("product"),
        "search_form": CandidateSearchForm(), "max_items": MAX_SHELF_ITEMS,
    })


@login_required
@require_POST
def shelf_delete(request, pk):
    shelf = get_object_or_404(Shelf, pk=pk, owner=request.user)
    shelf.delete()
    messages.success(request, f"Shelf \"{shelf.name}\" dihapus.")
    return redirect("shelves:mine")


@login_required
def shelf_candidates(request, pk):
    shelf = get_object_or_404(Shelf, pk=pk, owner=request.user)
    form = CandidateSearchForm(request.GET)
    query = form.cleaned_data["q"].strip() if form.is_valid() else ""
    products = Product.objects.filter(is_active=True).order_by("product_name", "pk")
    if query:
        products = products.filter(Q(product_name__icontains=query) | Q(brand__icontains=query))
    in_shelf = set(shelf.items.values_list("product_id", flat=True))
    page = paginate(request, products)
    return JsonResponse({"results": [{**product_card(p), "in_shelf": p.pk in in_shelf} for p in page],
                         "page": page.number, "num_pages": page.paginator.num_pages, "count": page.paginator.count})


@login_required
@require_POST
@transaction.atomic
def shelf_item_add(request, pk):
    shelf = get_object_or_404(Shelf.objects.select_for_update(), pk=pk, owner=request.user)
    form = ShelfItemForm(request.POST, shelf=shelf)
    if form.is_valid():
        try:
            with transaction.atomic():
                item = form.save()
        except IntegrityError:
            logger.warning("Duplicate product %s on shelf %s", form.cleaned_data["product"].pk, shelf.pk)
            form.add_error("product", "Produk ini sudah ada di shelf.")
    if not form.errors:
        shelf.save(update_fields=["updated_at"])
        if wants_json(request):
            return JsonResponse({"product": product_card(item.product), "item_count": shelf.items.count()}, status=201)
        messages.success(request, "Produk ditambahkan ke shelf.")
    else:
        error = " ".join(message for messages_ in form.errors.values() for message in messages_)
        if wants_json(request):
            return JsonResponse({"error": error}, status=400)
        messages.error(request, error)
    return redirect("shelves:edit", pk=shelf.pk)


@login_required
@require_POST
def shelf_item_remove(request, pk, product_id):
    shelf = get_object_or_404(Shelf, pk=pk, owner=request.user)
    get_object_or_404(ShelfItem, shelf=shelf, product_id=product_id).delete()
    shelf.save(update_fields=["updated_at"])
    if wants_json(request):
        return JsonResponse({"item_count": shelf.items.count()})
    messages.success(request, "Produk dikeluarkan dari shelf.")
    return redirect("shelves:edit", pk=shelf.pk)


@login_required
@require_POST
def shelf_save(request, pk):
    shelf = get_object_or_404(Shelf, pk=pk)
    if shelf.is_private and shelf.owner_id != request.user.pk:
        raise Http404
    saved = request.POST.get("saved") == "1"
    if saved:
        SavedShelf.objects.get_or_create(user=request.user, shelf=shelf)
    else:
        SavedShelf.objects.filter(user=request.user, shelf=shelf).delete()
    if wants_json(request):
        return JsonResponse({"saved": saved, "save_count": shelf.saves.count()})
    messages.success(request, "Shelf disimpan ke Shelf Saya." if saved else "Shelf dihapus dari Shelf Saya.")
    return redirect("shelves:detail", pk=shelf.pk)
