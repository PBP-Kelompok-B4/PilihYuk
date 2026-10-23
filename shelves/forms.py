from django import forms

from accounts.forms import Styled

from .models import Shelf

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
