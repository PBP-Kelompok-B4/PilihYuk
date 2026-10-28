NUTRIENT_FIELDS = {
    "protein": {"label": "Protein", "field": "proteins_100g", "unit": "g", "scale": 1},
    "fiber": {"label": "Serat", "field": "fiber_100g", "unit": "g", "scale": 1},
    "sugar": {"label": "Gula", "field": "sugars_100g", "unit": "g", "scale": 1},
    "sodium": {"label": "Natrium", "field": "sodium_100g", "unit": "mg", "scale": 1000},
    "saturated_fat": {"label": "Lemak jenuh", "field": "saturated_fat_100g", "unit": "g", "scale": 1},
    "energy": {"label": "Kalori", "field": "energy_kcal_100g", "unit": "kkal", "scale": 1},
}
NUTRIENT_CHOICES = tuple((key, value["label"]) for key, value in NUTRIENT_FIELDS.items())
DIRECTION_CHOICES = (("max", "Maksimalkan ↑"), ("min", "Batasi ↓"))
DEFAULT_DIRECTION = "max"
DEFAULT_DIRECTIONS = {key: "max" if key in ("protein", "fiber") else "min" for key in NUTRIENT_FIELDS}
WEIGHT_CHOICES = ((1, "Rendah"), (2, "Sedang"), (3, "Tinggi"))
DEFAULT_WEIGHT = 2
WRITE_LIMIT = 30
WRITE_WINDOW_SECONDS = 60
