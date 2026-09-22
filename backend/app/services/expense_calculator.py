"""
Expense Calculator — deterministic, Decimal-based expense splitting.

IMPORTANT: This module does ALL financial calculations.
The LLM is NEVER used for calculations.

Rounding Strategy (ADR-003):
- Python Decimal with ROUND_HALF_UP
- Last participant absorbs any rounding remainder
- Total of shares always equals the original amount exactly
"""

from decimal import Decimal, ROUND_HALF_UP


def quantize(value: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_equal_split(amount: Decimal, n_participants: int) -> list[Decimal]:
    """
    Split amount equally among n_participants.

    The last participant absorbs any rounding remainder, ensuring
    the sum of all shares equals the original amount exactly.

    Args:
        amount: Total expense amount. Must be positive.
        n_participants: Number of participants. Must be >= 1.

    Returns:
        List of share amounts. len(result) == n_participants.
        sum(result) == amount (exactly).

    Raises:
        ValueError: If amount <= 0 or n_participants < 1.

    Examples:
        >>> calculate_equal_split(Decimal("100"), 3)
        [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')]

        >>> calculate_equal_split(Decimal("100"), 2)
        [Decimal('50.00'), Decimal('50.00')]

        >>> calculate_equal_split(Decimal("10"), 3)
        [Decimal('3.33'), Decimal('3.33'), Decimal('3.34')]
    """
    if amount <= Decimal("0"):
        raise ValueError(f"Amount must be positive, got {amount}")
    if n_participants < 1:
        raise ValueError(f"Number of participants must be >= 1, got {n_participants}")

    if n_participants == 1:
        return [quantize(amount)]

    # Calculate per-person share (rounded)
    per_person = quantize(amount / n_participants)

    # First N-1 participants get the rounded share
    shares = [per_person] * (n_participants - 1)

    # Last participant gets whatever remains (handles rounding exactly)
    last_share = amount - sum(shares)

    shares.append(last_share)
    return shares


def validate_expense_amount(amount: Decimal) -> None:
    """Raise ValueError if amount is not valid for an expense."""
    if amount <= Decimal("0"):
        raise ValueError("Expense amount must be positive")
    if amount > Decimal("99999999.99"):
        raise ValueError("Expense amount is unreasonably large")
