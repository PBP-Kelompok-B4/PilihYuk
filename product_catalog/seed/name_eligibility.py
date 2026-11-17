"""Conservative CSV name screening; ambiguous names remain eligible for review."""
import re
import unicodedata

# Word boundaries avoid substring matches such as food 'conditioners' in ingredients.
NON_FOOD = re.compile(
    r"\b(?:sabun|soap|shampoo|sampo|shampo|deterjen|detergen|detergent|"
    r"toothpaste|toothbrush|pasta gigi|sikat gigi|body wash|facial wash|facial foam|"
    r"floor cleaner|bathroom cleaner|toilet cleaning|dishwash(?:ing)?(?: liquid)?|"
    r"sabun cuci|pembersih lantai|pemutih pakaian|fabric softener|"
    r"hand sanitiz(?:er|ing)|hand sanitiser|deodorant|deodoran|sunscreen|sunblock|"
    r"body lotion|body booster lotion|body serum|hair serum|scalp serum|"
    r"parfum|parfume|perfume|skincare|lipstick|lip tint|lip cream|eyeliner|"
    r"nail polish|hair colou?r|pembersih wajah|vitamin rambut|"
    r"disinfectant|disinfectan|lamp oil|cleansing oil|face tonic|face mist|"
    r"bb cream|baby powder|baby wipes|cotton buds|tissue|tisue|tisu|"
    r"rokok|cigarettes?|pembalut|diapers?|baterai|racun tikus)\b", re.I)
AMBIGUOUS = re.compile(
    r"\b(?:cream|conditioner|softener|serum|toner|mask|cushion|spray|clean|cleaner|"
    r"skin|beauty|bath|body|vitamin|multivitamin|supplement|suplemen|obat|"
    r"catfood|dog food|pet food|minyak kayu putih|powder)\b", re.I)
PLACEHOLDERS = {"null", "none", "nan", "unknown", "not applicable", "test", "testing",
                "asdf", "asdfgh", "asdfghjkl", "qwerty", "qwertyuiop", "abcdef", "xxx"}


def screen_name(name):
    """Return (rejection reason or None, manual review reason or None).

    No probabilistic gibberish/language/brand inference: unknown words survive.
    Normalize only for matching; callers retain their original mapped name.
    """
    normalized = " ".join(unicodedata.normalize("NFKC", name or "").casefold().split())
    if not normalized:
        return "empty_name", None
    if not any(char.isalpha() for char in normalized):
        return "numeric_or_symbol_only_name", None
    if normalized in PLACEHOLDERS:
        return "placeholder_or_keyboard_sequence", None
    match = NON_FOOD.search(normalized)
    if match:
        return "non_food:" + match.group(0), None
    ambiguous = AMBIGUOUS.search(normalized)
    if ambiguous:
        return None, "ambiguous_name:" + ambiguous.group(0)
    if len(normalized) <= 2 or not any(char.isspace() for char in normalized):
        return None, "short_or_single_token_name_not_verified"
    return None, None
