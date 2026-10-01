from tenderlens.document import build_document, clean_text, needs_ocr


def test_clean_text_drops_garbled_devanagari_and_keeps_english_values():
    raw = "बड\nबड\n \n \nववरण\n/\n/Minimum Average Annual Turnover of the\nbidder (For 3 Years)\n500 Lakh (s)\nरा!य\n (\n"
    assert clean_text(raw) == "/Minimum Average Annual Turnover of the\nbidder (For 3 Years)\n500 Lakh (s)"


def test_clean_text_drops_duplicated_short_glyph_pairs_but_keeps_single_values():
    raw = "7\n7\n (3\n (3\n/Total Quantity\n1\n5A\n5A\n/Years of Past Experience\n3 Year (s)"
    assert clean_text(raw) == "/Total Quantity\n1\n/Years of Past Experience\n3 Year (s)"


def test_clean_text_keeps_plain_english_untouched():
    assert clean_text("Bid End Date/Time\n23-10-2026 16:00:00") == "Bid End Date/Time\n23-10-2026 16:00:00"


def test_build_document_marks_pages():
    doc = build_document({1: "Bid document", 2: "Eligibility criteria"})
    assert doc == "[[PAGE 1]]\nBid document\n\n[[PAGE 2]]\nEligibility criteria"


def test_build_document_within_budget_keeps_all_pages_in_order():
    pages = {i: f"page {i} text" for i in range(1, 6)}
    doc = build_document(pages, budget_chars=10_000)
    assert [line for line in doc.splitlines() if line.startswith("[[PAGE")] == [f"[[PAGE {i}]]" for i in range(1, 6)]


def test_build_document_over_budget_keeps_most_relevant_pages_in_page_order():
    filler = "technical specification of the item " * 20
    pages = {
        1: "Bid End Date. EMD amount. Estimated value. " + filler,
        2: filler,
        3: "Eligibility: minimum average annual turnover, past experience of similar works. " + filler,
        4: filler,
        5: "Liquidated damages, penalty, performance security, termination. " + filler,
    }
    doc = build_document(pages, budget_chars=len(pages[3]) * 3 + 200)
    kept = [int(line[7:-2]) for line in doc.splitlines() if line.startswith("[[PAGE")]
    assert kept == [1, 3, 5]


def test_needs_ocr_for_nearly_empty_pages():
    assert needs_ocr("   \n 12 ")
    assert not needs_ocr("Minimum average annual turnover of Rs 50 Lakh for last three years")
