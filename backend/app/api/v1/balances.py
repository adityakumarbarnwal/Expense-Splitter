"""
Balances and Settlements API route handlers.

Endpoints:
  GET  /api/v1/groups/{id}/balances              — Net balances for all members
  GET  /api/v1/groups/{id}/settlements            — Settlement history
  POST /api/v1/groups/{id}/settlements            — Record a settlement
  DELETE /api/v1/groups/{id}/settlements/{sid}    — Delete a settlement
"""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.group import Group, Member
from app.models.settlement import Settlement
from app.schemas.settlement import (
    SettlementCreate,
    SettlementResponse,
    BalanceResponse,
    GroupBalancesResponse,
    SettlementSuggestion,
)
from app.services.balance_engine import calculate_group_balances
from app.services.settlement_engine import generate_settlement_suggestions

router = APIRouter(tags=["balances", "settlements"])


def _get_group_or_404(db: Session, group_id: int) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id={group_id} not found",
        )
    return group


@router.get("/groups/{group_id}/balances", response_model=GroupBalancesResponse)
def get_group_balances(
    group_id: int, db: Session = Depends(get_db)
) -> GroupBalancesResponse:
    """
    Get net balances for all members and settlement suggestions.

    Balances are calculated in Python using Decimal — NOT by the LLM.
    Positive balance: member is owed money.
    Negative balance: member owes money.
    """
    _get_group_or_404(db, group_id)

    raw_balances = calculate_group_balances(db, group_id)

    EPSILON = Decimal("0.005")

    balance_responses = [
        BalanceResponse(
            member_id=data["member_id"],
            member_name=data["member_name"],
            net_balance=data["net_balance"].quantize(Decimal("0.01")),
            total_paid=data["total_paid"].quantize(Decimal("0.01")),
            total_owed=data["total_owed"].quantize(Decimal("0.01")),
        )
        for data in raw_balances.values()
    ]

    suggestions_raw = generate_settlement_suggestions(raw_balances)
    suggestions = [
        SettlementSuggestion(
            from_member_id=s["from_member_id"],
            from_member_name=s["from_member_name"],
            to_member_id=s["to_member_id"],
            to_member_name=s["to_member_name"],
            amount=s["amount"],
        )
        for s in suggestions_raw
    ]

    is_settled = all(
        abs(b.net_balance) < EPSILON for b in balance_responses
    )

    return GroupBalancesResponse(
        group_id=group_id,
        balances=balance_responses,
        settlement_suggestions=suggestions,
        is_settled=is_settled,
    )


@router.get("/groups/{group_id}/settlements", response_model=list[SettlementResponse])
def list_settlements(
    group_id: int, db: Session = Depends(get_db)
) -> list[SettlementResponse]:
    """List all settlement records for a group."""
    _get_group_or_404(db, group_id)
    settlements = db.execute(
        select(Settlement)
        .where(Settlement.group_id == group_id)
        .order_by(Settlement.created_at.desc())
    ).scalars().all()

    return [
        SettlementResponse(
            id=s.id,
            group_id=s.group_id,
            payer_id=s.payer_id,
            payer_name=s.payer.name if s.payer else "",
            receiver_id=s.receiver_id,
            receiver_name=s.receiver.name if s.receiver else "",
            amount=s.amount,
            note=s.note,
            created_at=s.created_at,
        )
        for s in settlements
    ]


@router.post(
    "/groups/{group_id}/settlements",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_settlement(
    group_id: int,
    data: SettlementCreate,
    db: Session = Depends(get_db),
) -> SettlementResponse:
    """
    Record a settlement payment.

    Business rules:
    - Both payer and receiver must be group members
    - Amount must be positive (validated by schema)
    - Payer and receiver must be different (validated by schema)
    """
    group = _get_group_or_404(db, group_id)
    group_member_ids = {m.id for m in group.members}

    if data.payer_id not in group_member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payer with id={data.payer_id} is not a member of group {group_id}",
        )

    if data.receiver_id not in group_member_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Receiver with id={data.receiver_id} is not a member of group {group_id}",
        )

    settlement = Settlement(
        group_id=group_id,
        payer_id=data.payer_id,
        receiver_id=data.receiver_id,
        amount=Decimal(str(data.amount)),
        note=data.note,
    )
    db.add(settlement)
    db.commit()
    db.refresh(settlement)

    return SettlementResponse(
        id=settlement.id,
        group_id=settlement.group_id,
        payer_id=settlement.payer_id,
        payer_name=settlement.payer.name if settlement.payer else "",
        receiver_id=settlement.receiver_id,
        receiver_name=settlement.receiver.name if settlement.receiver else "",
        amount=settlement.amount,
        note=settlement.note,
        created_at=settlement.created_at,
    )


@router.delete(
    "/groups/{group_id}/settlements/{settlement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_settlement(
    group_id: int, settlement_id: int, db: Session = Depends(get_db)
) -> None:
    """Delete a settlement record."""
    _get_group_or_404(db, group_id)
    settlement = db.execute(
        select(Settlement).where(
            Settlement.id == settlement_id,
            Settlement.group_id == group_id,
        )
    ).scalar_one_or_none()

    if settlement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Settlement {settlement_id} not found in group {group_id}",
        )

    db.delete(settlement)
    db.commit()
