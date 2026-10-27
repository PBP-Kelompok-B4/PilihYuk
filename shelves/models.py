from django.conf import settings
from django.db import models

from product_catalog.models import Product

MAX_SHELF_ITEMS = 12

class Shelf(models.Model):
    name = models.CharField(max_length=100)
    store_context = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shelves")
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.name


class ShelfItem(models.Model):
    shelf = models.ForeignKey(Shelf, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="shelf_items")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["added_at"]
        constraints = [models.UniqueConstraint(fields=["shelf", "product"], name="unique_shelf_product")]

    def __str__(self):
        return f"{self.shelf} - {self.product}"


class SavedShelf(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_shelves")
    shelf = models.ForeignKey(Shelf, on_delete=models.CASCADE, related_name="saves")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "shelf"], name="unique_saved_shelf")]

    def __str__(self):
        return f"{self.user} - {self.shelf}"
