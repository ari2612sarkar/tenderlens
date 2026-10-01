from tenderlens.document import build_document, needs_ocr


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
