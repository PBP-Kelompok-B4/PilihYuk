from django.conf import settings
from django.db import models


class Product(models.Model):
    NUTRITION_GRADES = [(grade, grade) for grade in ("a", "b", "c", "d", "e", "unknown", "not-applicable")]
    ENVIRONMENTAL_GRADES = [
        (grade, grade)
        for grade in ("a-plus", "a", "b", "c", "d", "e", "f", "unknown", "not-applicable")
    ]

    code = models.CharField(max_length=14, unique=True, null=True, blank=True)
    product_name = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=255, blank=True)
    quantity = models.CharField(max_length=100, blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    category = models.CharField(max_length=100, blank=True, db_index=True)
    origin = models.CharField(max_length=255, blank=True)

    nutrition_grade = models.CharField(max_length=14, choices=NUTRITION_GRADES, default="unknown", db_index=True)
    environmental_grade = models.CharField(max_length=14, choices=ENVIRONMENTAL_GRADES, default="unknown")
    environmental_grade_estimated = models.CharField(max_length=20, blank=True)
    nova_group = models.IntegerField(choices=[(value, value) for value in range(1, 5)], null=True, blank=True)

    energy_kcal_100g = models.FloatField(null=True, blank=True)
    proteins_100g = models.FloatField(null=True, blank=True)
    fat_100g = models.FloatField(null=True, blank=True)
    saturated_fat_100g = models.FloatField(null=True, blank=True)
    carbohydrates_100g = models.FloatField(null=True, blank=True)
    sugars_100g = models.FloatField(null=True, blank=True)
    fiber_100g = models.FloatField(null=True, blank=True)
    sodium_100g = models.FloatField(null=True, blank=True)

    # This records the presence of a label, not a claim about halal status.
    halal_labeled = models.BooleanField(default=False)
    ingredients_text = models.TextField(blank=True)
    allergens = models.JSONField(default=list, blank=True)
    serving_size = models.CharField(max_length=100, blank=True)
    categories_tags = models.JSONField(default=list, blank=True)
    packaging_tags = models.JSONField(default=list, blank=True)
    labels_tags = models.JSONField(default=list, blank=True)
    ingredients_analysis_tags = models.JSONField(default=list, blank=True)
    misc_tags = models.JSONField(default=list, blank=True)

    source = models.CharField(max_length=6, choices=[("off", "off"), ("manual", "manual")])
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)


class ProductView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
