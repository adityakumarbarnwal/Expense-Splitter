"""
Balance Engine — calculates net balances for all group members.

IMPORTANT: All calculations use Decimal. LLM is never involved.

Balance calculation:
  For each member:
    total_paid = sum of expenses where member is payer
    total_owed = sum of shares assigned to member across all expenses
    net_balance = total_paid - total_owed + settlements_received - settlements_paid

  Positive net_balance: Member is owed money (others owe them)
  Negative net_balance: Member owes money (they owe others)
  Zero: Settled
"""

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.group import Member
from app.models.expense import Expense, ExpenseParticipant
from app.models.settlement import Settlement


def calculate_group_balances(
    db: Session, group_id: int
) -> dict[int, dict]:
    """
    Calculate net balance for every member in the group.

    Returns a dict mapping member_id to:
    {
        "member_id": int,
        "member_name": str,
        "total_paid": Decimal,   # total amount paid as payer
        "total_owed": Decimal,   # total share owed across all expenses
        "net_balance": Decimal,  # total_paid - total_owed (+ settlements delta)
    }
    """
    # Fetch all members of the group
    members = db.execute(
        select(Member).where(Member.group_id == group_id)
    ).scalars().all()

    if not members:
        return {}

    # Initialize balance dict
    balances: dict[int, dict] = {
        m.id: {
            "member_id": m.id,
            "member_name": m.name,
            "total_paid": Decimal("0.00"),
            "total_owed": Decimal("0.00"),
            "settlements_paid": Decimal("0.00"),
            "settlements_received": Decimal("0.00"),
            "net_balance": Decimal("0.00"),
        }
        for m in members
    }

    member_ids = set(balances.keys())

    # Calculate total_paid: amount each member paid as payer
    expenses = db.execute(
        select(Expense).where(Expense.group_id == group_id)
    ).scalars().all()

    for expense in expenses:
        if expense.payer_id in balances:
            balances[expense.payer_id]["total_paid"] += Decimal(str(expense.amount))

    # Calculate total_owed: sum of shares assigned to each member
    participants = db.execute(
        select(ExpenseParticipant)
        .join(Expense, ExpenseParticipant.expense_id == Expense.id)
        .where(Expense.group_id == group_id)
    ).scalars().all()

    for participant in participants:
        if participant.member_id in balances:
            balances[participant.member_id]["total_owed"] += Decimal(str(participant.share))

    # Calculate settlement effects
    settlements = db.execute(
        select(Settlement).where(Settlement.group_id == group_id)
    ).scalars().all()

    for settlement in settlements:
        amount = Decimal(str(settlement.amount))
        if settlement.payer_id in balances:
            balances[settlement.payer_id]["settlements_paid"] += amount
        if settlement.receiver_id in balances:
            balances[settlement.receiver_id]["settlements_received"] += amount

    # Compute net balance for each member
    # net = total_paid - total_owed + settlements_paid - settlements_received
    #
    # settlements_paid: money you paid to others (clearing your debt)
    #   → increases your net (your debt is reduced / credit grows)
    # settlements_received: money others paid you (satisfying their debt to you)
    #   → decreases your net (your outstanding credit is now consumed)
    for member_id, data in balances.items():
        data["net_balance"] = (
            data["total_paid"]
            - data["total_owed"]
            + data["settlements_paid"]
            - data["settlements_received"]
        )

    return balances
