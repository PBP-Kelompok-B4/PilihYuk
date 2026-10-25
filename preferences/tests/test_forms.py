from django.test import TestCase

from preferences.forms import DecisionForm, PreferenceForm
from preferences.models import Preference
from .helpers import make_product, make_shelf, make_user


class PreferenceFormTests(TestCase):
    def setUp(self):
        self.user = make_user()

    def test_invalid_weight_and_duplicate_have_friendly_errors(self):
        for weight in (0, 4, "1.5", "abc", ""):
            form = PreferenceForm({"nutrient": "protein", "direction": "max", "weight": weight}, user=self.user)
            self.assertFalse(form.is_valid())
            self.assertIn("weight", form.errors)
        Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        form = PreferenceForm({"nutrient": "protein", "direction": "max", "weight": 2}, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("sudah aktif", str(form.errors))

    def test_edit_cannot_change_nutrient_or_owner(self):
        item = Preference.objects.create(user=self.user, nutrient="protein", direction="max")
        form = PreferenceForm({"nutrient": "sugar", "direction": "min", "weight": 3, "user": 999},
                              user=self.user, instance=item)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual((saved.nutrient, saved.user, saved.direction, saved.weight), ("protein", self.user, "min", 3))


class DecisionFormTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.product = make_product()
        self.other = make_user("lain")

    def test_optional_shelf_and_note_but_required_active_product(self):
        self.assertTrue(DecisionForm({"product": self.product.pk}, user=self.user).is_valid())
        inactive = make_product(is_active=False)
        for data in ({}, {"product": inactive.pk}, {"product": self.product.pk, "note": "x" * 501}):
            form = DecisionForm(data, user=self.user)
            self.assertFalse(form.is_valid())

    def test_shelf_visibility_and_product_membership(self):
        own = make_shelf(self.user, self.product, is_private=True)
        public = make_shelf(self.other, self.product)
        private = make_shelf(self.other, self.product, is_private=True)
        empty = make_shelf(self.user)
        for shelf, expected in ((own, True), (public, True), (private, False), (empty, False)):
            form = DecisionForm({"product": self.product.pk, "shelf": shelf.pk}, user=self.user)
            self.assertEqual(form.is_valid(), expected, form.errors)
