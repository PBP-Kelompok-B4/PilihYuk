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
    compared_product_ids = forms.ModelMultipleChoiceField(queryset=Product.objects.none(), required=False,
                                                         widget=forms.MultipleHiddenInput)

    class Meta:
        model = Decision
        fields = ("product", "shelf", "note")
        labels = {"shelf": "Shelf asal (opsional)", "note": "Alasan (opsional)"}
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "maxlength": 500})}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user
        self.fields["product"].queryset = Product.objects.filter(is_active=True).order_by("product_name", "pk")
        self.fields["compared_product_ids"].queryset = Product.objects.filter(is_active=True)
        self.fields["shelf"].queryset = Shelf.objects.filter(Q(owner=user) | Q(is_private=False)).order_by("name", "pk")
        # Riwayat lama tetap bisa disunting walau relasi asal sudah dihapus.
        if self.instance.pk:
            self.fields.pop("product")
            self.fields.pop("shelf")
            self.fields.pop("compared_product_ids")
        for field in self.fields.values():
            field.widget.attrs["class"] = "w-full min-w-0 rounded-xl border border-line bg-white p-3 text-sm focus-visible:outline-brand"

    def clean(self):
        data = super().clean()
        product, shelf = data.get("product"), data.get("shelf")
        if product and shelf and not shelf.items.filter(product=product, product__is_active=True).exists():
            self.add_error("shelf", "Produk tidak ada di shelf ini.")
        if not self.instance.pk and "compared_product_ids" in self.data:
            raw = self.data.getlist("compared_product_ids") if hasattr(self.data, "getlist") else self.data["compared_product_ids"]
            subset = data.get("compared_product_ids")
            if not isinstance(raw, (list, tuple)) or not 1 <= len(raw) <= 4 or len(set(raw)) != len(raw):
                self.add_error("compared_product_ids", "Pilih 1 sampai 4 ID produk unik tanpa duplikasi.")
            elif not shelf:
                self.add_error("compared_product_ids", "Subset pembanding wajib disertai shelf yang dapat diakses.")
            elif subset is not None:
                ids = {item.pk for item in subset}
                if (len(ids) != len(raw) or not product or product.pk not in ids
                        or shelf.items.filter(product_id__in=ids, product__is_active=True).count() != len(ids)):
                    self.add_error("compared_product_ids", "Subset harus berisi produk aktif di shelf dan mencakup produk pilihan.")
                else:
                    self.instance.compared_product_count = len(ids)
        return data


class DecisionFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Nama produk atau merek", max_length=255)
    shelf = forms.ModelChoiceField(queryset=Shelf.objects.none(), required=False, label="Shelf",
                                   empty_label="Semua shelf")
    dari = forms.DateField(required=False, label="Dari tanggal", input_formats=["%Y-%m-%d"],
                           widget=forms.DateInput(attrs={"type": "date"}))
    sampai = forms.DateField(required=False, label="Sampai tanggal", input_formats=["%Y-%m-%d"],
                             widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shelf"].queryset = Shelf.objects.filter(Q(owner=user) | Q(is_private=False)).order_by("name", "pk")
        for name, field in self.fields.items():
            field.widget.attrs["id"] = f"filter-{name}"
            field.widget.attrs["class"] = "w-full min-w-0 rounded-xl border border-line bg-white p-3 text-sm focus-visible:outline-brand"


class DecisionBulkDeleteForm(forms.Form):
    ids = forms.Field(widget=forms.SelectMultiple, label="Keputusan yang dipilih")

    def clean_ids(self):
        values = self.cleaned_data["ids"]
        if len(values) > 100:
            raise forms.ValidationError("Pilih maksimal 100 keputusan sekaligus.")
        identifier = forms.IntegerField(min_value=1, max_value=9223372036854775807)
        return list(dict.fromkeys(identifier.clean(value) for value in values))
