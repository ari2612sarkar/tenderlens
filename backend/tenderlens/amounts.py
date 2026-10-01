"""Parse Indian-format rupee amounts ("₹ 2.5 Crore", "Rs. 50,00,000", "75 Lakhs")."""

import re

_UNITS = {"crore": 10_000_000, "cr": 10_000_000, "lakh": 100_000, "lac": 100_000}

_AMOUNT_RE = re.compile(
    r"(?P<num>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>crores?|cr\b\.?|lakhs?|lacs?\b)?",
    re.IGNORECASE,
)


def parse_inr(text: str) -> int | None:
    """Return the first rupee amount in `text` as whole rupees, or None."""
    match = _AMOUNT_RE.search(text or "")
    if not match:
        return None
    value = float(match.group("num").replace(",", ""))
    unit = (match.group("unit") or "").lower().rstrip(".")
    for prefix, multiplier in _UNITS.items():
        if unit.startswith(prefix):
            value *= multiplier
            break
    return round(value)


def amounts_agree(amount_inr: int, amount_text: str, tolerance: float = 0.01) -> bool:
    """True when the model's numeric amount matches what the source text says."""
    parsed = parse_inr(amount_text)
    if parsed is None or parsed == 0:
        return False
    return abs(amount_inr - parsed) <= tolerance * parsed
