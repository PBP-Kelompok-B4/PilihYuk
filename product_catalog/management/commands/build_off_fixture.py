"""Export a local OFF CSV/gzip dump to a validated fixture, without DB writes."""
import hashlib
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from product_catalog.models import Product
from product_catalog.seed.off_mapping import product_fields, has_valid_nutriscore
from product_catalog.seed import seed_dataset
from product_catalog.open_food_facts import read_indonesian_products_from_csv, normalize_barcode
from product_catalog.seed.name_eligibility import screen_name
from product_catalog.seed.seed_exclusions import load_seed_exclusions


class Command(BaseCommand):
    help = "Export Indonesian OFF CSV records to JSON; no HTTP or database writes."

    def add_arguments(self, parser):
        parser.add_argument("--csv", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--limit", type=int, default=406)

    def handle(self, *args, **options):
        if options["limit"] < 1:
            raise CommandError("limit must be positive")
        source, output = Path(options["csv"]), Path(options["output"])
        if source.resolve() == output.resolve():
            raise CommandError("Output must differ from source")
        fixture, seen, skipped = [], set(), 0
        try:
            excluded = load_seed_exclusions()
            manifest = seed_dataset.load_seed_dataset()
            excluded -= set(manifest["seed_only_exclusion_overrides"])
            seed_codes = set(manifest["canonical_barcodes"])
            for record in read_indonesian_products_from_csv(source):
                try:
                    raw_code = record.get("code", "")
                    if not isinstance(raw_code, str) or not raw_code.isascii() or not raw_code.isdigit() or len(raw_code) > 14:
                        raise ValueError("invalid source barcode")
                    if (normalize_barcode(raw_code) in excluded or not has_valid_nutriscore(record)
                            or not seed_dataset.is_seed_member(normalize_barcode(raw_code), seed_codes)):
                        skipped += 1
                        continue
                    fields = product_fields(record)
                    for key in ("product_name_id", "product_name", "product_name_en"):
                        name = record.get(key)
                        if isinstance(name, str) and name.strip() and name.strip() == fields["product_name"]:
                            fields["product_name"] = name
                            break
                    if screen_name(fields["product_name"])[0]:
                        skipped += 1
                        continue
                    Product(**fields).full_clean(validate_unique=False, validate_constraints=False)
                    if fields["code"] in seen:
                        skipped += 1
                        continue
                except (ValueError, ValidationError):
                    skipped += 1
                    continue
                seen.add(fields["code"])
                fields.update(is_active=True, added_by=None, last_synced_at=None,
                              created_at="2026-10-10T00:00:00Z", updated_at="2026-10-10T00:00:00Z")
                fixture.append({"model": "product_catalog.product", "pk": len(fixture) + 1, "fields": fields})
                if len(fixture) >= options["limit"]:
                    break
            if not fixture:
                raise CommandError("No valid Indonesian records found; output was not written")
            # Stream hashing: source dump can be multiple gigabytes.
            digest = hashlib.sha256()
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            output.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            output.with_suffix(output.suffix + ".provenance.json").write_text(json.dumps({
                "source_file": source.name, "source_sha256": digest.hexdigest(), "count": len(fixture),
                "selection": "reviewed 406 membership, exact Indonesia, known Nutri-Score; 62 seed-only exceptions",
                "mapping": "product_catalog.seed.off_mapping.product_fields", "licenses": "ODbL; DbCL; CC BY-SA",
            }, indent=2) + "\n", encoding="utf-8")
        except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
            raise CommandError(f"CSV export failed: {type(exc).__name__}") from exc
        self.stdout.write(self.style.SUCCESS(f"Exported {len(fixture)} products; skipped {skipped} invalid/duplicate records."))
