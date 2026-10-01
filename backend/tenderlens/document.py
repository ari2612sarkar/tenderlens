"""Turn a tender PDF into page-numbered text the agents can cite."""

import io
import re

from pypdf import PdfReader

# Words that signal eligibility, commercial terms or risk; used to rank pages when a document is too long.
_KEYWORDS = (
    "eligib", "qualif", "turnover", "experience", "similar", "net worth", "emd", "earnest", "bid security",
    "estimated", "bid end", "due date", "penalt", "liquidated", "performance security", "bank guarantee",
    "termination", "payment", "msme", "mse", "micro", "startup", "exempt", "certificat", "iso", "registration",
    "blacklist", "debar", "liabilit", "indemn", "intellectual property", "warranty", "document",
)

DEFAULT_BUDGET_CHARS = 350_000


_DEVANAGARI = re.compile(r"[ऀ-ॿ]+")
_HAS_CONTENT = re.compile(r"[A-Za-z0-9]")


def clean_text(text: str) -> str:
    """Drop the (usually garbled) Hindi half of bilingual GeM labels and lines left with no content."""
    lines = [_DEVANAGARI.sub("", line).rstrip() for line in text.splitlines()]
    lines = [line for line in lines if _HAS_CONTENT.search(line)]

    # Legacy Hindi fonts leave short Latin glyph pairs ("7\n7", "5A\n5A"); real values appear once.
    def is_glyph_pair(i: int) -> bool:
        s = lines[i].strip()
        return len(s) <= 3 and any(0 <= j < len(lines) and lines[j].strip() == s for j in (i - 1, i + 1))

    return "\n".join(line for i, line in enumerate(lines) if not is_glyph_pair(i))


def pdf_pages(data: bytes) -> dict[int, str]:
    """Extract cleaned text per page (1-indexed)."""
    reader = PdfReader(io.BytesIO(data))
    return {i: clean_text(page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)}


def needs_ocr(text: str) -> bool:
    return len(re.sub(r"\s", "", text)) < 40


def _score(text: str) -> int:
    lower = text.lower()
    return sum(lower.count(k) for k in _KEYWORDS)


def build_document(pages: dict[int, str], budget_chars: int = DEFAULT_BUDGET_CHARS) -> str:
    """Join pages with [[PAGE n]] markers; if over budget keep the most relevant pages, in page order."""
    blocks = {n: f"[[PAGE {n}]]\n{pages[n].strip()}" for n in sorted(pages)}
    if sum(len(b) + 2 for b in blocks.values()) <= budget_chars:
        return "\n\n".join(blocks.values())
    keep, used = set(), 0
    for n in sorted(pages, key=lambda n: (-_score(pages[n]), n)):
        size = len(blocks[n]) + 2
        if used + size <= budget_chars:
            keep.add(n)
            used += size
    return "\n\n".join(blocks[n] for n in sorted(keep))
