"""Load the development fixture without replacing existing products or IDs."""

import json

from django.core.management.base import BaseCommand
from django.db import transaction

from product_catalog.fixture_data import FIXTURE
from product_catalog.models import Product


class Command(BaseCommand):
    help = "Add the 20 OFF fixture products; skip existing barcodes without changing them."

    @transaction.atomic
    def handle(self, *args, **options):
        records = json.loads(FIXTURE.read_text(encoding="utf-8"))
        created = 0
        for record in records:
            fields = record["fields"].copy()
            # Let Django assign local IDs and creation/update timestamps.
            fields.pop("created_at")
            fields.pop("updated_at")
            if Product.objects.filter(code=fields["code"]).exists():
                continue
            product = Product(**fields)
            product.full_clean()
            product.save()
            created += 1
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} products; kept {len(records) - created} existing products unchanged."
        ))
