"""
Expenses API route handlers.

Endpoints:
  GET  /api/v1/groups/{id}/expenses       — List expenses for a group
  POST /api/v1/groups/{id}/expenses       — Add an expense
  GET  /api/v1/groups/{id}/expenses/{eid} — Get expense detail
  DELETE /api/v1/groups/{id}/expenses/{eid} — Delete an expense
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.group import Group, Member
from app.models.expense import Expense, ExpenseParticipant
from app.schemas.expense import ExpenseCreate, ExpenseResponse, ExpenseParticipantResponse
from app.services.expense_calculator import calculate_equal_split

router = APIRouter(tags=["expenses"])


def _get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id={group_id} not found",
        )
    return group


def _build_expense_response(expense: Expense) -> ExpenseResponse:
    """Build a complete ExpenseResponse from an ORM object."""
    participants = [
        ExpenseParticipantResponse(
            id=p.id,
            member_id=p.member_id,
            member_name=p.member.name if p.member else "",
            share=p.share,
        )
        for p in expense.participants
    ]
    return ExpenseResponse(
        id=expense.id,
        group_id=expense.group_id,
        description=expense.description,
        amount=expense.amount,
        payer_id=expense.payer_id,
        payer_name=expense.payer.name if expense.payer else "",
        note=expense.note,
        created_at=expense.created_at,
        participants=participants,
    )


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseResponse])
def list_expenses(group_id: int, db: Session = Depends(get_db)) -> list[ExpenseResponse]:
    """List all expenses for a group in reverse chronological order."""
    _get_group_or_404(db, group_id)
    expenses = db.execute(
        select(Expense)
        .where(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
    ).scalars().all()
    return [_build_expense_response(e) for e in expenses]


@router.post(
    "/groups/{group_id}/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(
    group_id: int,
    data: ExpenseCreate,
    db: Session = Depends(get_db),
) -> ExpenseResponse:
    """
    Add a shared expense to a group.

    Business rules validated here:
    - Group must exist
    - Payer must be a group member
    - All participants must be group members
    - Amount must be positive (validated by schema)
    - At least one participant required (validated by schema)

    The equal split is calculated by expense_calculator.py (NOT the LLM).
    """
    group = _get_group_or_404(db, group_id)

    # Build member lookup for this group
    group_members = {m.id: m for m in group.members}

    # Validate payer
    if data.payer_id not in group_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payer with id={data.payer_id} is not a member of group {group_id}",
        )

    # Validate participants
    invalid_participants = [pid for pid in data.participant_ids if pid not in group_members]
    if invalid_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The following participant IDs are not group members: {invalid_participants}",
        )

    # Calculate shares using the deterministic calculator (Decimal, ROUND_HALF_UP)
    amount = Decimal(str(data.amount))
    n_participants = len(data.participant_ids)
    shares = calculate_equal_split(amount, n_participants)

    # Sort participants alphabetically for deterministic share assignment
    sorted_participant_ids = sorted(data.participant_ids, key=lambda pid: group_members[pid].name)

    # Create the expense
    expense = Expense(
        group_id=group_id,
        description=data.description,
        amount=amount,
        payer_id=data.payer_id,
        note=data.note,
    )
    db.add(expense)
    db.flush()  # Get the expense ID before creating participants

    # Create expense participants
    for participant_id, share in zip(sorted_participant_ids, shares):
        participant = ExpenseParticipant(
            expense_id=expense.id,
            member_id=participant_id,
            share=share,
        )
        db.add(participant)

    db.commit()
    db.refresh(expense)

    return _build_expense_response(expense)


@router.get(
    "/groups/{group_id}/expenses/{expense_id}",
    response_model=ExpenseResponse,
)
def get_expense(
    group_id: int, expense_id: int, db: Session = Depends(get_db)
) -> ExpenseResponse:
    """Get a specific expense."""
    _get_group_or_404(db, group_id)
    expense = db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == group_id,
        )
    ).scalar_one_or_none()

    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense {expense_id} not found in group {group_id}",
        )

    return _build_expense_response(expense)


@router.delete(
    "/groups/{group_id}/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_expense(
    group_id: int, expense_id: int, db: Session = Depends(get_db)
) -> None:
    """Delete an expense (and all its participants via cascade)."""
    _get_group_or_404(db, group_id)
    expense = db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == group_id,
        )
    ).scalar_one_or_none()

    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Expense {expense_id} not found in group {group_id}",
        )

    db.delete(expense)
    db.commit()
