"""
Balance engine for MongoDB-backed data.

Calculates net balances for all members of a group based on:
- Expenses (paid vs. owed shares)
- Settlements (payments between members)

Returns per-member net balance using float arithmetic
(rounded to 2 decimal places for display).

Formula:
  net = total_paid - total_owed + settlements_paid - settlements_received

Positive net = you are owed money.
Negative net = you owe money.
"""

import logging
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)
EPSILON = 0.005  # Amounts smaller than this are treated as zero


async def calculate_group_balances(
    db: AsyncIOMotorDatabase,
    group_id: str,
    member_ids: list[str],
    member_names: dict[str, str],  # {user_id: name}
) -> dict[str, dict]:
    """
    Calculate net balances for all group members.

    Returns dict keyed by user_id:
    {
        user_id: {
            "user_id": str,
            "member_name": str,
            "total_paid": float,
            "total_owed": float,
            "settlements_paid": float,
            "settlements_received": float,
            "net_balance": float,
        }
    }
    """
    # Initialize balance tracking
    balances: dict[str, dict] = {}
    for uid in member_ids:
        balances[uid] = {
            "user_id": uid,
            "member_name": member_names.get(uid, "Unknown"),
            "total_paid": 0.0,
            "total_owed": 0.0,
            "settlements_paid": 0.0,
            "settlements_received": 0.0,
            "net_balance": 0.0,
        }

    # Process expenses
    async for expense in db.expenses.find({"group_id": group_id}):
        payer_id = expense["payer_id"]
        amount = float(expense["amount"])

        if payer_id in balances:
            balances[payer_id]["total_paid"] += amount

        for participant in expense.get("participants", []):
            uid = participant["user_id"]
            share = float(participant["share"])
            if uid in balances:
                balances[uid]["total_owed"] += share

    # Process settlements
    async for settlement in db.settlements.find({"group_id": group_id}):
        payer_id = settlement["payer_id"]
        receiver_id = settlement["receiver_id"]
        amount = float(settlement["amount"])

        if payer_id in balances:
            balances[payer_id]["settlements_paid"] += amount
        if receiver_id in balances:
            balances[receiver_id]["settlements_received"] += amount

    # Compute net balances
    for uid, data in balances.items():
        net = (
            data["total_paid"]
            - data["total_owed"]
            + data["settlements_paid"]
            - data["settlements_received"]
        )
        data["net_balance"] = round(net, 2)
        data["total_paid"] = round(data["total_paid"], 2)
        data["total_owed"] = round(data["total_owed"], 2)
        data["settlements_paid"] = round(data["settlements_paid"], 2)
        data["settlements_received"] = round(data["settlements_received"], 2)

    return balances


def generate_settlement_suggestions(
    balances: dict[str, dict],
) -> list[dict]:
    """
    Generate minimal settlement suggestions using greedy creditor-debtor matching.

    Returns list of:
    {
        "from_user_id": str,
        "from_member_name": str,
        "to_user_id": str,
        "to_member_name": str,
        "amount": float,
    }
    """
    creditors = []  # (amount, user_id, name) — positive net (owed money)
    debtors = []    # (amount, user_id, name) — negative net (owe money)

    for uid, data in balances.items():
        net = data["net_balance"]
        if net > EPSILON:
            creditors.append([net, uid, data["member_name"]])
        elif net < -EPSILON:
            debtors.append([-net, uid, data["member_name"]])

    # Sort descending by amount for efficient matching
    creditors.sort(key=lambda x: -x[0])
    debtors.sort(key=lambda x: -x[0])

    suggestions = []
    i, j = 0, 0

    while i < len(creditors) and j < len(debtors):
        cred_amt, cred_id, cred_name = creditors[i]
        debt_amt, debt_id, debt_name = debtors[j]

        payment = round(min(cred_amt, debt_amt), 2)
        if payment > EPSILON:
            suggestions.append({
                "from_user_id": debt_id,
                "from_member_name": debt_name,
                "to_user_id": cred_id,
                "to_member_name": cred_name,
                "amount": payment,
            })

        creditors[i][0] = round(cred_amt - payment, 2)
        debtors[j][0] = round(debt_amt - payment, 2)

        if creditors[i][0] <= EPSILON:
            i += 1
        if debtors[j][0] <= EPSILON:
            j += 1

    return suggestions
