from django import forms
from django.db.models import Q

from product_catalog.models import Product
from shelves.models import Shelf

from .constants import DEFAULT_WEIGHT, WEIGHT_CHOICES
from .models import Decision, Preference


class PreferenceForm(forms.ModelForm):
    weight = forms.TypedChoiceField(choices=WEIGHT_CHOICES, coerce=int, initial=DEFAULT_WEIGHT,
                                   error_messages={"invalid_choice": "Bobot harus 1 sampai 3."})

    class Meta:
        model = Preference
        fields = ("nutrient", "direction", "weight")

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        if self.instance.pk:
            self.fields["nutrient"].disabled = True

    def clean_nutrient(self):
        nutrient = self.cleaned_data["nutrient"]
        existing = Preference.objects.filter(user=self.instance.user, nutrient=nutrient)
        if existing.exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Preferensi nutrien ini sudah aktif.")
        return nutrient


class ProductChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, product):
        return f"{product.product_name} · {product.brand}" if product.brand else product.product_name


class DecisionForm(forms.ModelForm):
    product = ProductChoiceField(queryset=Product.objects.none(), label="Produk")

    class Meta:
        model = Decision
        fields = ("product", "shelf", "note")
        labels = {"shelf": "Shelf asal (opsional)", "note": "Alasan (opsional)"}
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "maxlength": 500})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("product_name", "pk")
        self.fields["shelf"].queryset = Shelf.objects.filter(Q(owner=user) | Q(is_private=False)).order_by("name", "pk")
        # Riwayat lama tetap bisa disunting walau relasi asal sudah dihapus.
        if self.instance.pk:
            self.fields.pop("product")
            self.fields.pop("shelf")
        for field in self.fields.values():
            field.widget.attrs["class"] = "w-full min-w-0 rounded-xl border border-line bg-white p-3 text-sm focus-visible:outline-brand"

    def clean(self):
        data = super().clean()
        product, shelf = data.get("product"), data.get("shelf")
        if product and shelf and not shelf.items.filter(product=product, product__is_active=True).exists():
            self.add_error("shelf", "Produk tidak ada di shelf ini.")
        return data
