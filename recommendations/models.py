from django.conf import settings
from django.db import models
from django.db.models import F, Q

from product_catalog.models import Product


class Recommendation(models.Model):
    source_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="outgoing_recommendations",
    )
    replacement_product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="incoming_recommendations",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendations",
    )
    reason = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recommendations_recommendation"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_product", "replacement_product"],
                name="unique_recommendation_direction",
            ),
            models.CheckConstraint(
                condition=~Q(source_product=F("replacement_product")),
                name="different_recommendation_products",
            ),
        ]

    def __str__(self):
        return f"{self.source_product.product_name} → {self.replacement_product.product_name}"


class RecommendationVote(models.Model):
    AGREE = 1
    DISAGREE = -1
    VOTE_CHOICES = [
        (AGREE, "Setuju"),
        (DISAGREE, "Tidak setuju"),
    ]

    recommendation = models.ForeignKey(
        Recommendation,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recommendation_votes",
    )
    value = models.SmallIntegerField(choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "recommendations_recommendation_vote"
        constraints = [
            models.UniqueConstraint(
                fields=["recommendation", "user"],
                name="one_vote_per_user_per_recommendation",
            ),
            models.CheckConstraint(
                condition=Q(value__in=[1, -1]),
                name="recommendation_vote_is_agree_or_disagree",
            ),
        ]

    def __str__(self):
        return f"{self.user} {'setuju' if self.value == self.AGREE else 'tidak setuju'}"
