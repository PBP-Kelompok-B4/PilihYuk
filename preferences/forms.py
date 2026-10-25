from django import forms

from .constants import DEFAULT_WEIGHT, WEIGHT_CHOICES
from .models import Preference


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
