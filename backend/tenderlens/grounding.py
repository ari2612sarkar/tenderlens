"""Verify that every quote the model cites really appears on (or next to) the cited page."""

import re

from rapidfuzz import fuzz

_MIN_FUZZY_LEN = 20
_THRESHOLD = 90


def _normalize(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)  # re-join words hyphenated across line breaks
    text = text.translate(str.maketrans({"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', " ": " "}))
    return re.sub(r"\s+", " ", text).strip().lower()


def _candidates(page: int, pages: dict[int, str]) -> list[str]:
    near = [p for p in (page - 1, page, page + 1) if p in pages]
    texts = [pages[p] for p in near]
    texts += [pages[p] + "\n" + pages[p + 1] for p in near if p + 1 in near]
    return [_normalize(t) for t in texts]


def quote_on_page(quote: str, page: int, pages: dict[int, str]) -> bool:
    q = _normalize(quote or "")
    if not q:
        return False
    candidates = _candidates(page, pages)
    if len(q) < _MIN_FUZZY_LEN:
        return any(q in c for c in candidates)
    numbers = re.findall(r"\d+(?:\.\d+)?", q)
    for c in candidates:
        if all(n in c for n in numbers) and fuzz.partial_ratio(q, c) >= _THRESHOLD:
            return True
    return False


def ground_items(items: list[dict], pages: dict[int, str]) -> list[dict]:
    """Return copies of `items` with `grounded` set from their quote and page."""
    return [{**item, "grounded": quote_on_page(item.get("quote", ""), int(item.get("page") or 0), pages)}
            for item in items]
