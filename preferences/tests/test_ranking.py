from django.test import TestCase

from preferences.models import Preference
from preferences.ranking import order_metric_rows, rank_products
from .helpers import build_product


class MetricOrderTests(TestCase):
    def test_weights_then_default_order_with_unknown_keys_at_end(self):
        rows = ["energy", "protein", "fat", "fiber", "sugar", "custom"]
        preferences = [Preference(nutrient="fiber", weight=3), Preference(nutrient="protein", weight=2),
                       Preference(nutrient="sugar", weight=2)]
        with self.assertNumQueries(0):
            result = order_metric_rows(preferences, rows)
        self.assertEqual(result, ["fiber", "protein", "sugar", "energy", "fat", "custom"])
        self.assertEqual(rows, ["energy", "protein", "fat", "fiber", "sugar", "custom"])

    def test_equal_weights_use_default_order_and_ignore_unknown_preferences(self):
        preferences = [Preference(nutrient="sugar", weight=3), Preference(nutrient="protein", weight=3),
                       Preference(nutrient="custom", weight=3)]
        self.assertEqual(order_metric_rows(iter(preferences), ["energy", "protein", "sugar", "custom"]),
                         ["protein", "sugar", "energy", "custom"])
        self.assertEqual(order_metric_rows([], ["protein", "fiber", "custom"]), ["protein", "fiber", "custom"])
        self.assertEqual(order_metric_rows(preferences, []), [])


class ProductRankingTests(TestCase):
    def test_max_and_min_keep_zero_known_and_missing_last(self):
        zero = build_product(proteins_100g=0)
        missing = build_product(proteins_100g=None)
        high = build_product(proteins_100g=10)
        products = [zero, missing, high]
        preference = Preference(nutrient="protein", direction="max", weight=2)
        with self.assertNumQueries(0):
            self.assertEqual(rank_products(products, [preference]), [high, zero, missing])
            preference.direction = "min"
            self.assertEqual(rank_products(products, [preference]), [zero, high, missing])
        self.assertEqual(products, [zero, missing, high])

    def test_weight_changes_which_product_comes_first(self):
        protein = build_product(proteins_100g=10, sugars_100g=1000)
        sugar = build_product(proteins_100g=0, sugars_100g=0)
        preferences = [Preference(nutrient="protein", direction="max", weight=3),
                       Preference(nutrient="sugar", direction="min", weight=1)]
        self.assertEqual(rank_products([sugar, protein], preferences), [protein, sugar])
        preferences[0].weight, preferences[1].weight = 1, 3
        self.assertEqual(rank_products([protein, sugar], preferences), [sugar, protein])

    def test_partial_missing_data_is_not_a_zero_value(self):
        complete = build_product(proteins_100g=10, sugars_100g=10)
        partial = build_product(proteins_100g=5, sugars_100g=None)
        zero = build_product(proteins_100g=0, sugars_100g=0)
        missing = build_product()
        preferences = [Preference(nutrient="protein", direction="max", weight=1),
                       Preference(nutrient="sugar", direction="min", weight=3)]
        self.assertEqual(rank_products([partial, missing, complete, zero], preferences),
                         [zero, complete, partial, missing])

    def test_equal_values_and_equal_scores_are_stable(self):
        first = build_product(proteins_100g=2)
        second = build_product(proteins_100g=2)
        preference = Preference(nutrient="protein", direction="max", weight=2)
        self.assertEqual(rank_products([first, second], [preference]), [first, second])
        preference.direction = "min"
        self.assertEqual(rank_products([second, first], [preference]), [second, first])
        missing = build_product()
        self.assertEqual(rank_products([missing, second, first], [preference]), [second, first, missing])

    def test_empty_inputs_all_missing_and_no_active_preferences(self):
        first, second = build_product(), build_product()
        preference = Preference(nutrient="protein", direction="max", weight=2)
        self.assertEqual(rank_products([], [preference]), [])
        self.assertEqual(rank_products([first, second], []), [first, second])
        self.assertEqual(rank_products([first, second], [preference]), [first, second])
        self.assertEqual(rank_products([first, second], [Preference(nutrient="custom")]), [first, second])

    def test_only_passed_preferences_influence_ranking_and_iterables_are_supported(self):
        protein = build_product(proteins_100g=10, sugars_100g=10)
        sugar = build_product(proteins_100g=0, sugars_100g=0)
        active = Preference(nutrient="protein", direction="max", weight=1)
        with self.assertNumQueries(0):
            result = rank_products(iter([sugar, protein]), iter([active]))
        self.assertEqual(result, [protein, sugar])
