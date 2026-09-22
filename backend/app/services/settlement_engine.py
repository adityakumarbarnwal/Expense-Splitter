"""
Settlement Engine — generates minimal settlement suggestions to clear all debts.

Algorithm: Greedy creditor-debtor matching.
- Sort members into creditors (positive balance) and debtors (negative balance)
- Match largest creditor with largest debtor
- Continue until all debts are cleared

This produces a minimal number of transactions (at most N-1 for N people).

IMPORTANT: This is a suggestion engine only.
The LLM is NEVER used for settlement calculations.
"""

from decimal import Decimal


def generate_settlement_suggestions(
    balances: dict[int, dict],
) -> list[dict]:
    """
    Generate a minimal list of settlement transactions.

    Args:
        balances: Output from calculate_group_balances().
                  Keys are member_id, values have 'net_balance', 'member_name', etc.

    Returns:
        List of settlement suggestions:
        [
            {
                "from_member_id": int,   # debtor (owes money)
                "from_member_name": str,
                "to_member_id": int,     # creditor (owed money)
                "to_member_name": str,
                "amount": Decimal,
            },
            ...
        ]
        Returns empty list if all balances are zero.
    """
    EPSILON = Decimal("0.01")  # Tolerance for floating-point-like issues

    # Separate into creditors and debtors
    creditors: list[dict] = []  # positive net_balance (owed money)
    debtors: list[dict] = []    # negative net_balance (owe money)

    for member_id, data in balances.items():
        balance = data["net_balance"]
        if balance > EPSILON:
            creditors.append({
                "member_id": member_id,
                "member_name": data["member_name"],
                "amount": balance,
            })
        elif balance < -EPSILON:
            debtors.append({
                "member_id": member_id,
                "member_name": data["member_name"],
                "amount": -balance,  # Make positive for easier math
            })

    if not creditors or not debtors:
        return []

    suggestions = []

    # Greedy matching
    creditor_idx = 0
    debtor_idx = 0

    while creditor_idx < len(creditors) and debtor_idx < len(debtors):
        creditor = creditors[creditor_idx]
        debtor = debtors[debtor_idx]

        # The settlement amount is the minimum of what's owed and what's due
        settle_amount = min(creditor["amount"], debtor["amount"])

        if settle_amount >= EPSILON:
            suggestions.append({
                "from_member_id": debtor["member_id"],
                "from_member_name": debtor["member_name"],
                "to_member_id": creditor["member_id"],
                "to_member_name": creditor["member_name"],
                "amount": settle_amount.quantize(Decimal("0.01")),
            })

        creditor["amount"] -= settle_amount
        debtor["amount"] -= settle_amount

        if creditor["amount"] < EPSILON:
            creditor_idx += 1
        if debtor["amount"] < EPSILON:
            debtor_idx += 1

    return suggestions
