from django import forms

from .models import Product
from .open_food_facts import normalize_barcode


def has_valid_gtin(barcode):
    if not isinstance(barcode, str) or len(barcode) not in (8, 12, 13, 14):
        return False
    if not barcode.isascii() or not barcode.isdigit():
        return False
    total = sum(int(digit) * (3 if index % 2 == 0 else 1)
                for index, digit in enumerate(reversed(barcode[:-1])))
    return int(barcode[-1]) == (-total) % 10


class BarcodeLookupForm(forms.Form):
    barcode = forms.CharField(
        label="Barcode", max_length=40,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "spellcheck": "false"}),
    )

    def clean_barcode(self):
        raw = self.cleaned_data["barcode"]
        if any(char not in "0123456789 -" for char in raw):
            raise forms.ValidationError("Barcode hanya boleh berisi angka, spasi, atau tanda hubung.")
        digits = raw.replace(" ", "").replace("-", "")
        normalized = normalize_barcode(digits)
        if not has_valid_gtin(digits) or not has_valid_gtin(normalized):
            raise forms.ValidationError("Gunakan barcode GTIN 8, 12, 13, atau 14 digit dengan check digit yang valid.")
        return normalized


class ManualProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("product_name", "brand", "quantity", "category", "origin",
                  "ingredients_text", "serving_size", "image_url", "nutrition_grade",
                  "environmental_grade", "nova_group", "halal_labeled", "allergens",
                  "packaging_tags", "energy_kcal_100g", "proteins_100g", "fat_100g",
                  "saturated_fat_100g", "carbohydrates_100g", "sugars_100g",
                  "fiber_100g", "sodium_100g")

    product_name = forms.CharField(label="Nama produk", max_length=255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs["rows"] = 4
            if not isinstance(field.widget, forms.CheckboxInput):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (
                    f"{existing} block w-full min-w-0 rounded-lg border border-line p-3"
                ).strip()
        for key in ("nutrition_grade", "environmental_grade"):
            self.fields[key].required = False

    def clean(self):
        import math
        values = super().clean()
        for key in ("nutrition_grade", "environmental_grade"):
            values[key] = values.get(key) or "unknown"
        for key in ("allergens", "packaging_tags"):
            value = values.get(key)
            if value in (None, ""):
                values[key] = []
            elif not isinstance(value, list) or any(not isinstance(tag, str) for tag in value):
                self.add_error(key, "Gunakan daftar tag JSON berupa teks.")
        for key in ("energy_kcal_100g", "proteins_100g", "fat_100g", "saturated_fat_100g",
                    "carbohydrates_100g", "sugars_100g", "fiber_100g", "sodium_100g"):
            value = values.get(key)
            if value is not None and (not math.isfinite(value) or value < 0):
                self.add_error(key, "Gunakan angka tidak negatif yang valid.")
        return values
