import pytest

from tenderlens.amounts import amounts_agree, parse_inr


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Rs. 50,00,000", 5_000_000),
        ("₹ 2.5 Crore", 25_000_000),
        ("INR 75 Lakhs", 7_500_000),
        ("Rs 1.20 lakh", 120_000),
        ("₹12,34,567/-", 1_234_567),
        ("3 Cr.", 30_000_000),
        ("Rs. 40 Lacs", 4_000_000),
        ("5,000,000 INR", 5_000_000),
        ("Rs. 10 Lakh (Rupees Ten Lakh only)", 1_000_000),
    ],
)
def test_parse_inr_handles_indian_formats(text, expected):
    assert parse_inr(text) == expected


@pytest.mark.parametrize("text", ["", "not specified", "as per BoQ"])
def test_parse_inr_returns_none_when_no_amount(text):
    assert parse_inr(text) is None


def test_amounts_agree_within_one_percent():
    assert amounts_agree(25_000_000, "₹ 2.5 Crore")
    assert amounts_agree(25_100_000, "₹ 2.5 Crore")


def test_amounts_disagree_when_model_misreads_units():
    # model read "2.5 Crore" as 2.5 lakh
    assert not amounts_agree(250_000, "₹ 2.5 Crore")


def test_amounts_disagree_when_text_unparseable():
    assert not amounts_agree(1_000_000, "as per BoQ")
