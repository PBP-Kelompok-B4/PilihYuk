from django import forms

from accounts.forms import Styled
from product_catalog.models import Product

from .models import MAX_SHELF_ITEMS, Shelf, ShelfItem

DESCRIPTION_MAX = 280


class ShelfForm(Styled, forms.ModelForm):
    description = forms.CharField(
        label="Deskripsi", required=False, max_length=DESCRIPTION_MAX,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Kenapa produk-produk ini saling menggantikan?"}),
    )

    class Meta:
        model = Shelf
        fields = ["name", "store_context", "description", "is_private"]
        labels = {"name": "Nama shelf", "store_context": "Konteks", "is_private": "Privat"}
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Mie instan goreng di minimarket"}),
            "store_context": forms.TextInput(attrs={"placeholder": "Alfamart, kopi pagi di kos, kantin kampus"}),
        }


class CandidateSearchForm(Styled, forms.Form):
    q = forms.CharField(label="Cari produk", required=False, max_length=100,
                        widget=forms.TextInput(attrs={"type": "search", "placeholder": "Cari nama produk atau merek"}))


class ShelfItemForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.filter(is_active=True),
                                     error_messages={"invalid_choice": "Produk tidak ditemukan."})

    def __init__(self, *args, shelf, **kwargs):
        super().__init__(*args, **kwargs)
        self.shelf = shelf

    def clean_product(self):
        product = self.cleaned_data["product"]
        if self.shelf.items.filter(product=product).exists():
            raise forms.ValidationError("Produk ini sudah ada di shelf.")
        return product

    def clean(self):
        if self.shelf.items.count() >= MAX_SHELF_ITEMS:
            raise forms.ValidationError(f"Shelf maksimal berisi {MAX_SHELF_ITEMS} produk.")
        return super().clean()

    def save(self):
        return ShelfItem.objects.create(shelf=self.shelf, product=self.cleaned_data["product"])
