"""
Tests for expense calculation engine.

Covers US-05 acceptance criteria and ADR-003 rounding strategy.
"""

import pytest
from decimal import Decimal
from app.services.expense_calculator import calculate_equal_split, validate_expense_amount


class TestCalculateEqualSplit:
    """Tests for the equal-split calculation function."""

    def test_even_split_two_people(self):
        """₹100 split by 2 = ₹50 each."""
        shares = calculate_equal_split(Decimal("100"), 2)
        assert len(shares) == 2
        assert shares[0] == Decimal("50.00")
        assert shares[1] == Decimal("50.00")
        assert sum(shares) == Decimal("100.00")

    def test_uneven_split_three_people(self):
        """₹100 split by 3 = [33.33, 33.33, 33.34]. Last absorbs remainder."""
        shares = calculate_equal_split(Decimal("100"), 3)
        assert len(shares) == 3
        assert shares[0] == Decimal("33.33")
        assert shares[1] == Decimal("33.33")
        assert shares[2] == Decimal("33.34")
        assert sum(shares) == Decimal("100.00")

    def test_uneven_split_small_amount(self):
        """₹10 split by 3 = [3.33, 3.33, 3.34]."""
        shares = calculate_equal_split(Decimal("10"), 3)
        assert shares[0] == Decimal("3.33")
        assert shares[1] == Decimal("3.33")
        assert shares[2] == Decimal("3.34")
        assert sum(shares) == Decimal("10.00")

    def test_single_participant(self):
        """Single participant gets the full amount."""
        shares = calculate_equal_split(Decimal("500"), 1)
        assert len(shares) == 1
        assert shares[0] == Decimal("500.00")
        assert sum(shares) == Decimal("500.00")

    def test_sum_always_equals_original(self):
        """The sum of shares must ALWAYS equal the original amount."""
        test_cases = [
            (Decimal("100"), 3),
            (Decimal("1"), 3),
            (Decimal("0.01"), 3),
            (Decimal("1200"), 7),
            (Decimal("999.99"), 4),
            (Decimal("1000"), 6),
        ]
        for amount, n in test_cases:
            shares = calculate_equal_split(amount, n)
            assert sum(shares) == amount, (
                f"Sum mismatch: {sum(shares)} != {amount} for {amount}/{n}"
            )

    def test_large_amount(self):
        """Large amounts work correctly."""
        shares = calculate_equal_split(Decimal("50000"), 4)
        assert len(shares) == 4
        assert all(s == Decimal("12500.00") for s in shares)
        assert sum(shares) == Decimal("50000.00")

    def test_rounding_case_adr003(self):
        """Verify the ADR-003 example: ₹1 / 3 people."""
        shares = calculate_equal_split(Decimal("1"), 3)
        assert shares == [Decimal("0.33"), Decimal("0.33"), Decimal("0.34")]
        assert sum(shares) == Decimal("1.00")

    def test_zero_amount_raises(self):
        """Zero amount should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_equal_split(Decimal("0"), 2)

    def test_negative_amount_raises(self):
        """Negative amount should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            calculate_equal_split(Decimal("-100"), 2)

    def test_zero_participants_raises(self):
        """Zero participants should raise ValueError."""
        with pytest.raises(ValueError, match=">="):
            calculate_equal_split(Decimal("100"), 0)

    def test_amount_with_cents(self):
        """Amounts with cents split correctly."""
        shares = calculate_equal_split(Decimal("100.50"), 2)
        assert shares[0] == Decimal("50.25")
        assert shares[1] == Decimal("50.25")
        assert sum(shares) == Decimal("100.50")


class TestValidateExpenseAmount:
    def test_valid_amount(self):
        """Valid positive amount passes without exception."""
        validate_expense_amount(Decimal("500"))  # No exception

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            validate_expense_amount(Decimal("0"))

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            validate_expense_amount(Decimal("-1"))

    def test_too_large_raises(self):
        with pytest.raises(ValueError):
            validate_expense_amount(Decimal("100000000"))
