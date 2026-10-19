"""Import an OFF CSV or development fixture without replacing existing rows."""

import csv
import gzip
import json
from collections import Counter
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from product_catalog.seed_dataset import FINAL_FIXTURE as FIXTURE
from product_catalog import seed_dataset
from product_catalog.models import Product
from product_catalog.off_mapping import product_fields, has_valid_nutriscore
from product_catalog.open_food_facts import read_indonesian_products_from_csv, normalize_barcode
from product_catalog.name_eligibility import screen_name
from product_catalog.seed_exclusions import load_seed_exclusions


class Command(BaseCommand):
    help = "Import reviewed 406 seed members with known Nutri-Score; preserve existing rows."

    def add_arguments(self, parser):
        parser.add_argument("--fixture", default=str(FIXTURE))
        parser.add_argument("--csv", help="OFF CSV or CSV.gz; process all Indonesian rows")
        parser.add_argument("--dry-run", action="store_true", help="Validate and count without writes")
        parser.add_argument("--batch-size", type=int, default=200)
        parser.add_argument("--report-csv", help="Write per-input-row decisions outside the repository; .gz supported")

    def handle(self, *args, **options):
        if options["batch_size"] < 1:
            raise CommandError("batch-size must be positive")
        if options["csv"]:
            if options["fixture"] != str(FIXTURE):
                raise CommandError("Choose --csv or --fixture, not both")
            return self.seed_csv(options)
        if options["dry_run"]:
            raise CommandError("--dry-run requires --csv")
        return self.seed_fixture(options)

    def seed_csv(self, options):
        try:
            excluded_codes = load_seed_exclusions()
            manifest = seed_dataset.load_seed_dataset()
            excluded_codes -= set(manifest["seed_only_exclusion_overrides"])
            seed_codes = set(manifest["canonical_barcodes"])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError("Reviewed seed exclusions could not be loaded; seeding stopped") from exc
        stats, reasons, details, seen, batch = Counter(), Counter(), Counter(), set(), []
        created = would_create = 0
        report_stream = None
        writer = None
        if options.get("report_csv"):
            report_path = Path(options["report_csv"]).resolve()
            repository = Path(__file__).resolve().parents[3]
            if report_path.is_relative_to(repository) or report_path == Path(options["csv"]).resolve():
                raise CommandError("Report must be outside the repository and must not overwrite the source")
            try:
                report_stream = (gzip.open(report_path, "wt", encoding="utf-8-sig", newline="")
                                 if str(report_path).endswith(".gz") else
                                 report_path.open("w", encoding="utf-8-sig", newline=""))
            except OSError as exc:
                raise CommandError("Report could not be opened") from exc
            writer = csv.DictWriter(report_stream, fieldnames=["code", "product_name", "decision", "reason", "manual_review", "nutriscore_grade", "nutrition_grades"])
            writer.writeheader()

        def decision(record, name, result, reason, review=""):
            if writer:
                writer.writerow({"code": record.get("code", ""), "product_name": name,
                                 "decision": result, "reason": reason, "manual_review": review,
                                 "nutriscore_grade": record.get("nutriscore_grade", ""),
                                 "nutrition_grades": record.get("nutrition_grades", "")})

        def flush():
            nonlocal created, would_create
            if options["dry_run"]:
                for fields in batch:
                    if Product.objects.filter(code=fields["code"]).exists():
                        reasons["existing_barcode"] += 1
                    else:
                        would_create += 1
            else:
                inserted_count = existing_count = 0
                # A failing batch rolls back completely. Earlier batches remain committed.
                with transaction.atomic():
                    for fields in batch:
                        _, inserted = Product.objects.get_or_create(code=fields["code"], defaults=fields)
                        inserted_count += int(inserted)
                        existing_count += int(not inserted)
                created += inserted_count
                reasons["existing_barcode"] += existing_count
            batch.clear()

        failure = None
        try:
            reject_callback = (lambda record, reason: decision(record, record.get("product_name", ""), "rejected", reason)) if writer else None
            for record in read_indonesian_products_from_csv(options["csv"], stats=stats, reject_callback=reject_callback):
                raw = record.get("code", "")
                if not raw or not raw.isascii() or not raw.isdigit() or len(raw) > 14:
                    reasons["invalid_barcode"] += 1
                    decision(record, record.get("product_name", ""), "rejected", "invalid_barcode")
                    continue
                if normalize_barcode(raw) in excluded_codes:
                    reasons["reviewed_barcode_exclusion"] += 1
                    decision(record, record.get("product_name", ""), "rejected", "reviewed_barcode_exclusion")
                    continue
                if not has_valid_nutriscore(record):
                    reasons["invalid_nutriscore"] += 1
                    decision(record, record.get("product_name", ""), "rejected", "invalid_nutriscore")
                    continue
                if not seed_dataset.is_seed_member(normalize_barcode(raw), seed_codes):
                    reasons["outside_final_dataset"] += 1
                    decision(record, record.get("product_name", ""), "rejected", "outside_final_dataset")
                    continue
                try:
                    fields = product_fields(record)
                    # Keep the selected source name, including original casing/spacing.
                    for key in ("product_name_id", "product_name", "product_name_en"):
                        value = record.get(key)
                        if isinstance(value, str) and value.strip() == fields["product_name"] and value.strip():
                            fields["product_name"] = value
                            break
                    rejection, review = screen_name(fields["product_name"])
                    if rejection:
                        key = "non_food_name" if rejection.startswith("non_food:") else "unusable_name"
                        reasons[key] += 1
                        decision(record, fields["product_name"], "rejected", rejection)
                        continue
                    if fields["code"] in seen:
                        reasons["duplicate_csv"] += 1
                        decision(record, fields["product_name"], "rejected", "duplicate_csv")
                        continue
                    Product(**fields).full_clean(validate_unique=False, validate_constraints=False)
                except (ValueError, ValidationError) as exc:
                    reasons["validation"] += 1
                    decision(record, record.get("product_name", ""), "rejected", "existing_validation:" + type(exc).__name__)
                    # Log error categories/field names, never source values or raw rows.
                    if isinstance(exc, ValidationError):
                        for key in getattr(exc, "message_dict", {"model": []}):
                            details[f"validation_field_{key}"] += 1
                    else:
                        details["invalid_grade_or_mapping"] += 1
                    continue
                seen.add(fields["code"])
                stats["accepted"] += 1
                stats["manual_review"] += int(bool(review))
                stats["accepted_without_valid_nutriscore"] += int(not has_valid_nutriscore(record))
                decision(record, fields["product_name"], "accepted", "eligible", review or "")
                batch.append(fields)
                if len(batch) >= options["batch_size"]:
                    flush()
            flush()
        except (OSError, EOFError, UnicodeError, ValueError, csv.Error) as exc:
            failure = f"CSV input failure ({type(exc).__name__}); inspect file/header/encoding"
            if type(exc) is ValueError or isinstance(exc, csv.Error):
                failure += f": {exc}"
            details["input_failure"] += 1
        except DatabaseError as exc:
            # Storage errors must stop the import; do not pretend a failed batch succeeded.
            failure = f"Import stopped ({type(exc).__name__}); current batch rolled back"
            details["storage_failure"] += 1
        finally:
            if report_stream:
                report_stream.close()
        skipped = sum(reasons.values()) + stats["non_indonesia"] + stats["malformed_row"]
        errors = reasons["validation"] + stats["malformed_row"] + int(failure is not None)
        self.stdout.write(json.dumps({
            "mode": "dry-run" if options["dry_run"] else "import",
            "rows_read": stats["rows_read"], "indonesia_rows": stats["indonesia_rows"],
            "accepted": stats["accepted"], "manual_review": stats["manual_review"],
            "accepted_without_valid_nutriscore": stats["accepted_without_valid_nutriscore"],
            "created": created, "would_create": would_create, "updated": 0,
            "skipped": skipped, "errors": errors,
            "skip_reasons": {"non_indonesia": stats["non_indonesia"], "malformed_row": stats["malformed_row"], **reasons},
            "error_causes": {"malformed_row": stats["malformed_row"], **details},
            "delimiter": stats.get("delimiter"), "encoding": stats.get("encoding"),
            "quoting": stats.get("quoting"),
            "completed": failure is None,
            "uncommitted_valid_rows": len(batch) if failure else 0,
        }, sort_keys=True))
        if failure:
            raise CommandError(failure)

    @transaction.atomic
    def seed_fixture(self, options):
        from pathlib import Path
        try:
            excluded = load_seed_exclusions()
            manifest = seed_dataset.load_seed_dataset()
            excluded -= set(manifest["seed_only_exclusion_overrides"])
            seed_codes = set(manifest["canonical_barcodes"])
            records = json.loads(Path(options["fixture"]).read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise CommandError("Fixture could not be read") from exc
        if not isinstance(records, list):
            raise CommandError("Fixture must be a list")
        created = skipped_policy = 0
        for record in records:
            if not isinstance(record, dict) or record.get("model") != "product_catalog.product" or not isinstance(record.get("fields"), dict):
                raise CommandError("Invalid fixture record")
            fields = record["fields"].copy()
            code = fields.get("code")
            if fields.get("source") != "off" or not isinstance(code, str) or not code.isascii() or not code.isdigit() or len(code) not in (8, 13, 14):
                raise CommandError("Fixture needs OFF records with canonical barcodes")
            # Let Django assign local IDs and creation/update timestamps.
            fields.pop("created_at", None)
            fields.pop("updated_at", None)
            if Product.objects.filter(code=fields["code"]).exists():
                continue
            product = Product(**fields)
            product.full_clean(validate_unique=False)
            if (normalize_barcode(code) != code or code in excluded
                    or not seed_dataset.is_seed_member(code, seed_codes)
                    or product.nutrition_grade not in "abcde" or len(product.nutrition_grade) != 1
                    or screen_name(product.product_name)[0]):
                skipped_policy += 1
                continue
            _, inserted = Product.objects.get_or_create(code=code, defaults={key: value for key, value in fields.items() if key != "code"})
            created += int(inserted)
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} products; skipped {skipped_policy} by reviewed name/barcode policy; kept existing products unchanged."
        ))
