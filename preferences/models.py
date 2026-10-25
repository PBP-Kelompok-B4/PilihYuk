from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models

from .constants import DEFAULT_WEIGHT, DIRECTION_CHOICES, NUTRIENT_CHOICES


class Preference(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="nutrition_preferences")
    nutrient = models.CharField(max_length=20, choices=NUTRIENT_CHOICES)
    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    weight = models.PositiveSmallIntegerField(default=DEFAULT_WEIGHT, validators=[MinValueValidator(1), MaxValueValidator(3)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "nutrient"], name="unique_user_nutrient")]

    def __str__(self):
        return f"{self.user}: {self.get_nutrient_display()} ({self.get_direction_display()}, {self.weight})"


class Decision(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="decisions")
    product = models.ForeignKey("product_catalog.Product", on_delete=models.SET_NULL, null=True)
    shelf = models.ForeignKey("shelves.Shelf", on_delete=models.SET_NULL, null=True, blank=True)
    note = models.TextField(blank=True, max_length=500, validators=[MaxLengthValidator(500)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        name = self.product.product_name if self.product else "Tidak diketahui"
        return f"{self.user}: {name} ({self.created_at})"
