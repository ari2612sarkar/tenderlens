from datetime import date

import pytest

from tenderlens.fy import last_completed_fys, normalize_fy


def test_last_completed_fys_after_april():
    assert last_completed_fys(3, date(2026, 10, 1)) == ["2025-26", "2024-25", "2023-24"]


def test_last_completed_fys_before_april():
    # Jan 2026 is inside FY 2025-26, so the last completed FY is 2024-25
    assert last_completed_fys(2, date(2026, 1, 15)) == ["2024-25", "2023-24"]


def test_last_completed_fys_on_april_first():
    assert last_completed_fys(1, date(2026, 4, 1)) == ["2025-26"]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("2024-25", "2024-25"),
        ("FY 2024-2025", "2024-25"),
        ("2024-2025", "2024-25"),
        ("FY24-25", "2024-25"),
        ("2024/25", "2024-25"),
        ("F.Y. 2023 - 24", "2023-24"),
    ],
)
def test_normalize_fy(text, expected):
    assert normalize_fy(text) == expected


def test_normalize_fy_rejects_garbage():
    assert normalize_fy("last three years") is None
