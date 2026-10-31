"""Runtime lookup support. Quota reservations commit before network access."""

import math

from django.db import DatabaseError
from django.db.models import F
from django.utils import timezone

from .models import OffLookupQuota, Product
from .seed.off_mapping import nutrition_grade
from .seed.name_eligibility import screen_name
from .seed.seed_exclusions import load_seed_exclusions
from .open_food_facts import normalize_barcode


def reserve_off_lookup(user):
    """Reserve one call in (now - 60s, now], or return retry seconds.

    The version predicate makes the UPDATE a compare-and-swap on both SQLite
    and PostgreSQL. A losing writer re-reads; lock/storage errors fail closed.
    No select_for_update assumption, process lock, or network transaction.
    """
    for _ in range(8):
        quota, _ = OffLookupQuota.objects.get_or_create(user=user)
        now = timezone.now().timestamp()
        recent = [stamp for stamp in quota.timestamps if stamp > now - 60]
        if len(recent) >= 3:
            return max(1, math.ceil(min(recent) + 60 - now))
        updated = OffLookupQuota.objects.filter(user=user, version=quota.version).update(
            timestamps=[*recent, now], version=F("version") + 1,
        )
        if updated:
            return 0
    raise DatabaseError("OFF quota reservation contention")


def save_imported_product(fields, user):
    """Validate, then let the unique barcode/get_or_create resolve insert races.

    Existing rows, including manual/inactive entries, are never updated.
    """
    product = Product(**fields, added_by=user, last_synced_at=timezone.now())
    try:
        product.nutrition_grade = nutrition_grade({"nutriscore_grade": product.nutrition_grade})
    except ValueError:
        product.nutrition_grade = "unknown"
    if product.source == "off" and (normalize_barcode(product.code) in load_seed_exclusions() or screen_name(product.product_name)[0]):
        raise ValueError("OFF import rejected by reviewed name/barcode policy")
    product.full_clean(validate_unique=False)
    defaults = {key: getattr(product, key) for key in fields if key != "code"}
    defaults.update(added_by=user, last_synced_at=product.last_synced_at)
    return Product.objects.get_or_create(code=product.code, defaults=defaults)[0]
