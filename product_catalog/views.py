from urllib.parse import quote

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Product
from .off_mapping import tag_name


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
    return render(request, "product_catalog/product_list.html", {
        "products": products.order_by("product_name", "pk"), "filters": filters,
        "options": options, "nutrition_grades": Product.NUTRITION_GRADES,
    })


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
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
        "packaging": [tag_name(tag) for tag in product.packaging_tags],
        "allergens": [tag_name(tag) for tag in product.allergens],
    })
