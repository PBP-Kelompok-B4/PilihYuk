from django import forms

from product_catalog.models import Product

from .models import Recommendation


class RecommendationForm(forms.ModelForm):
    class Meta:
        model = Recommendation
        fields = ("replacement_product", "reason")
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 5, "placeholder": "Jelaskan alasan penggantian ini."}),
        }

    def __init__(self, *args, source_product, **kwargs):
        super().__init__(*args, **kwargs)
        self.source_product = source_product
        candidates = Product.objects.none()
        if source_product.category:
            candidates = Product.objects.filter(
                is_active=True,
                category=source_product.category,
            ).exclude(pk=source_product.pk).order_by("product_name", "pk")
        self.fields["replacement_product"].queryset = candidates
        self.fields["replacement_product"].label = "Produk pengganti"
        self.fields["reason"].label = "Alasan"
        self.fields["replacement_product"].widget.attrs["class"] = "mt-2 w-full rounded-lg border border-line p-3"
        self.fields["reason"].widget.attrs["class"] = "mt-2 w-full rounded-lg border border-line p-3"

    def clean(self):
        cleaned = super().clean()
        replacement = cleaned.get("replacement_product")
        if replacement and Recommendation.objects.filter(
            source_product=self.source_product,
            replacement_product=replacement,
        ).exists():
            self.add_error("replacement_product", "Rekomendasi penggantian ini sudah ada.")
        return cleaned

    def save(self, *, author, commit=True):
        recommendation = super().save(commit=False)
        recommendation.source_product = self.source_product
        recommendation.author = author
        if commit:
            recommendation.save()
        return recommendation
