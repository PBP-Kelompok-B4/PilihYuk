from django.test import TestCase

from pilihyuk.views import SAMPLE_PRODUCTS, comparison_rows


class HomePageTests(TestCase):
    def test_best_values_are_marked(self):
        best = {r["label"]: [c["best"] for c in r["cells"]] for r in comparison_rows(SAMPLE_PRODUCTS)}
        self.assertEqual(best["Kalori"], [False] * 4)  # tidak dinilai
        self.assertEqual(best["Protein"], [True, False, False, False])  # tertinggi
        self.assertEqual(best["Gula"], [False, False, False, True])  # terendah
        self.assertEqual(best["Natrium"], [False, False, False, True])

    def test_missing_values_are_skipped(self):
        products = [{**SAMPLE_PRODUCTS[0], "protein": None}, SAMPLE_PRODUCTS[1]]
        protein = next(r for r in comparison_rows(products) if r["label"] == "Protein")
        self.assertEqual([c["best"] for c in protein["cells"]], [False, True])
        self.assertEqual(protein["cells"][0]["pct"], 0)

    def test_home_page_renders(self):
        response = self.client.get("/")
        self.assertContains(response, "Bandingkan sebelum pilih.")
        self.assertContains(response, "Tertinggi")
