from tenderlens.grounding import ground_items, quote_on_page

PAGES = {
    1: "BID DOCUMENT\nBid End Date/Time 15-10-2026 15:00:00\nMinimum Average Annual Turnover of the bidder (For 3 Years) 50 Lakh (s)",
    2: "Years of Past Experience Required for same/similar service 3 Year (s)\nThe bidder shall furnish a Perfor-\nmance Bank Guarantee of 5%",
    3: "of the contract value within 15 days of award. Liquidated damages at 0.5% per week subject to max 10%.",
}


def test_exact_quote_is_grounded():
    assert quote_on_page("Minimum Average Annual Turnover of the bidder (For 3 Years) 50 Lakh (s)", 1, PAGES)


def test_quote_with_whitespace_and_case_differences_is_grounded():
    assert quote_on_page("years of past experience required for   same/similar service 3 year (s)", 2, PAGES)


def test_quote_across_hyphenated_line_break_is_grounded():
    assert quote_on_page("furnish a Performance Bank Guarantee of 5%", 2, PAGES)


def test_quote_spanning_page_boundary_is_grounded():
    assert quote_on_page("Performance Bank Guarantee of 5% of the contract value within 15 days", 2, PAGES)


def test_quote_on_adjacent_page_is_grounded():
    # model cited page 2 but the text is on page 3
    assert quote_on_page("Liquidated damages at 0.5% per week subject to max 10%", 2, PAGES)


def test_fabricated_quote_is_not_grounded():
    assert not quote_on_page("Bidder must hold ISO 27001 certification", 1, PAGES)


def test_altered_number_is_not_grounded():
    assert not quote_on_page("Minimum Average Annual Turnover of the bidder (For 3 Years) 90 Crore", 1, PAGES)


def test_quote_on_distant_page_is_not_grounded():
    assert not quote_on_page("Liquidated damages at 0.5% per week subject to max 10%", 1, PAGES)


def test_short_quote_requires_exact_match():
    assert quote_on_page("3 Year (s)", 2, PAGES)
    assert not quote_on_page("4 Year (s)", 2, PAGES)


def test_ground_items_sets_flag_on_each_item():
    items = [
        {"quote": "Bid End Date/Time 15-10-2026 15:00:00", "page": 1},
        {"quote": "made up clause", "page": 1},
    ]
    grounded = ground_items(items, PAGES)
    assert [i["grounded"] for i in grounded] == [True, False]
