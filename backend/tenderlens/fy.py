"""Indian financial years (April to March), labelled like "2024-25"."""

import re
from datetime import date

_FY_RE = re.compile(r"(?:(?P<full>\d{4})|(?P<short>\d{2}))\s*[-/–]\s*(?P<end>\d{2,4})")


def _label(start_year: int) -> str:
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def last_completed_fys(n: int, as_of: date) -> list[str]:
    """The `n` most recent financial years that ended before `as_of`, newest first."""
    current_start = as_of.year if as_of.month >= 4 else as_of.year - 1
    return [_label(current_start - i) for i in range(1, n + 1)]


def normalize_fy(text: str) -> str | None:
    """Turn "FY 2024-2025", "FY24-25", "2024/25" etc. into "2024-25"."""
    match = _FY_RE.search(text or "")
    if not match:
        return None
    start = int(match.group("full")) if match.group("full") else 2000 + int(match.group("short"))
    return _label(start)
