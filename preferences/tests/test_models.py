from django.core.exceptions import ValidationError
from django.test import TestCase

from preferences.models import Preference
from .helpers import make_user


class PreferenceModelTests(TestCase):
    def test_default_weight_and_unique_nutrient_per_user(self):
        user = make_user()
        preference = Preference.objects.create(user=user, nutrient="protein", direction="max")
        self.assertEqual(preference.weight, 2)
        with self.assertRaises(ValidationError):
            Preference(user=user, nutrient="protein", direction="min").full_clean()
