from django.contrib.auth import get_user_model

from product_catalog.models import Product
from shelves.models import Shelf, ShelfItem


def make_user(name="pemilik"):
    return get_user_model().objects.create_user(username=name)


def make_product(**fields):
    return Product.objects.create(**{"product_name": "Produk contoh", "source": "manual", **fields})


def build_product(**fields):
    """Produk tanpa penyimpanan untuk pengujian fungsi murni."""
    return Product(**{"product_name": "Produk contoh", "source": "manual", **fields})


def make_shelf(owner, product=None, **fields):
    shelf = Shelf.objects.create(owner=owner, **{"name": "Shelf contoh", **fields})
    if product is not None:
        ShelfItem.objects.create(shelf=shelf, product=product)
    return shelf
