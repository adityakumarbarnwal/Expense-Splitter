"""
Expenses API routes — MongoDB backend.

All routes require authentication.
Authorization: user must be a group member.

Routes:
  GET    /api/v1/groups/:id/expenses         — List expenses
  POST   /api/v1/groups/:id/expenses         — Create expense
  GET    /api/v1/groups/:id/expenses/:eid    — Get expense detail
  PATCH  /api/v1/expenses/:eid               — Edit expense (any member)
  DELETE /api/v1/expenses/:eid               — Delete expense (any member)
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.auth import get_current_user
from app.db.database import get_database
from app.models.documents import ExpenseDocument, ExpenseParticipantDoc
from app.schemas.all_schemas import (
    CreateExpenseRequest,
    ExpenseParticipantResponse,
    ExpenseResponse,
    UpdateExpenseRequest,
)
from app.services.notification_service import notify_group_members

router = APIRouter(tags=["expenses"])
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _require_valid_oid(id_str: str, name: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail=f"Invalid {name}: {id_str!r}")
    return ObjectId(id_str)


async def _get_group_or_404(db, group_id_str: str) -> dict:
    oid = _require_valid_oid(group_id_str, "group ID")
    group = await db.groups.find_one({"_id": oid})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def _require_member(group: dict, user_id: str) -> None:
    if user_id not in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this group.",
        )


def _expense_to_response(expense: dict) -> ExpenseResponse:
    participants = [
        ExpenseParticipantResponse(
            user_id=p["user_id"],
            name=p["name"],
            share=p["share"],
        )
        for p in expense.get("participants", [])
    ]
    return ExpenseResponse(
        id=str(expense["_id"]),
        group_id=expense["group_id"],
        description=expense["description"],
        amount=expense["amount"],
        payer_id=expense["payer_id"],
        payer_name=expense["payer_name"],
        participants=participants,
        note=expense.get("note"),
        created_by=expense["created_by"],
        created_at=expense["created_at"],
        updated_at=expense["updated_at"],
    )


def _calculate_shares(amount: float, participant_ids: list[str]) -> dict[str, float]:
    """Equal split: last participant absorbs rounding remainder."""
    n = len(participant_ids)
    per_person = round(amount / n, 2)
    shares: dict[str, float] = {}
    running_total = 0.0

    sorted_ids = sorted(participant_ids)
    for i, uid in enumerate(sorted_ids):
        if i == n - 1:
            shares[uid] = round(amount - running_total, 2)
        else:
            shares[uid] = per_person
            running_total += per_person
    return shares


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseResponse])
async def list_expenses(
    group_id: str,
    current_user=Depends(get_current_user),
):
    """List all expenses in a group, newest first."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    expenses = await db.expenses.find(
        {"group_id": group_id},
        sort=[("created_at", -1)],
    ).to_list(500)

    return [_expense_to_response(e) for e in expenses]


@router.post("/groups/{group_id}/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
async def create_expense(
    group_id: str,
    data: CreateExpenseRequest,
    current_user=Depends(get_current_user),
):
    """
    Create a new expense in a group.

    Validations:
    - User must be a group member
    - Payer must be a group member
    - All participants must be group members
    - Amount > 0
    - No duplicate participants
    """
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    member_ids = group.get("member_ids", [])

    # Validate payer
    if data.payer_id not in member_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Payer (id={data.payer_id}) is not a member of this group.",
        )

    # Validate participants
    invalid = [pid for pid in data.participant_ids if pid not in member_ids]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"The following participant IDs are not group members: {invalid}",
        )

    # Look up user names
    user_name_map: dict[str, str] = {}
    for uid in set([data.payer_id] + data.participant_ids):
        if ObjectId.is_valid(uid):
            u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
            if u:
                user_name_map[uid] = u["name"]

    payer_name = user_name_map.get(data.payer_id, "Unknown")

    # Calculate shares
    shares = _calculate_shares(data.amount, data.participant_ids)
    participants = [
        ExpenseParticipantDoc(
            user_id=uid,
            name=user_name_map.get(uid, "Unknown"),
            share=shares[uid],
        )
        for uid in sorted(data.participant_ids)
    ]

    expense_doc = ExpenseDocument(
        group_id=group_id,
        description=data.description,
        amount=data.amount,
        payer_id=data.payer_id,
        payer_name=payer_name,
        participants=participants,
        note=data.note,
        created_by=user_id,
    )

    expense_dict = expense_doc.to_dict()
    # Convert participants to plain dicts
    expense_dict["participants"] = [p.model_dump() for p in participants]

    result = await db.expenses.insert_one(expense_dict)
    expense = await db.expenses.find_one({"_id": result.inserted_id})

    # Notify group members
    await notify_group_members(
        db=db,
        group=group,
        type="expense_added",
        message=f"{current_user['name']} added an expense: \"{data.description}\" "
                f"(₹{data.amount:,.2f}) in \"{group['name']}\".",
        related_entity_id=group_id,
        related_entity_type="group",
    )

    logger.info("Expense created: %s ₹%.2f in group %s", data.description, data.amount, group_id)
    return _expense_to_response(expense)


@router.get("/groups/{group_id}/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    group_id: str,
    expense_id: str,
    current_user=Depends(get_current_user),
):
    """Get a single expense detail."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    eid = _require_valid_oid(expense_id, "expense ID")
    expense = await db.expenses.find_one({"_id": eid, "group_id": group_id})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    return _expense_to_response(expense)


@router.patch("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: str,
    data: UpdateExpenseRequest,
    current_user=Depends(get_current_user),
):
    """
    Edit an existing expense.

    Authorization: any current group member can edit.

    When amount or participants change, shares are recalculated.
    Balance impact is always recomputed from the authoritative expense/settlement data.
    """
    db = get_database()
    user_id = str(current_user["_id"])
    eid = _require_valid_oid(expense_id, "expense ID")

    expense = await db.expenses.find_one({"_id": eid})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    # Get the group for member validation
    group = await db.groups.find_one({"_id": ObjectId(expense["group_id"])})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Authorization: any current group member can edit
    if user_id not in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this group to edit expenses.",
        )

    member_ids = group.get("member_ids", [])

    # Build update fields
    update_fields: dict = {"updated_at": datetime.now(timezone.utc)}

    if data.description is not None:
        update_fields["description"] = data.description.strip()

    # Determine effective payer and participants
    effective_payer_id = data.payer_id if data.payer_id is not None else expense["payer_id"]
    effective_participant_ids = data.participant_ids if data.participant_ids is not None else [
        p["user_id"] for p in expense.get("participants", [])
    ]
    effective_amount = data.amount if data.amount is not None else expense["amount"]

    # Validate payer
    if effective_payer_id not in member_ids:
        raise HTTPException(status_code=400, detail="Payer is not a group member.")

    # Validate participants
    invalid = [pid for pid in effective_participant_ids if pid not in member_ids]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid participants: {invalid}")

    # Update payer
    if data.payer_id is not None:
        if ObjectId.is_valid(effective_payer_id):
            payer_user = await db.users.find_one({"_id": ObjectId(effective_payer_id)}, {"name": 1})
            update_fields["payer_id"] = effective_payer_id
            update_fields["payer_name"] = payer_user["name"] if payer_user else "Unknown"

    # Recalculate shares if amount or participants changed
    if data.amount is not None or data.participant_ids is not None:
        update_fields["amount"] = effective_amount

        # Fetch user names
        user_name_map: dict[str, str] = {}
        for uid in effective_participant_ids:
            if ObjectId.is_valid(uid):
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
                if u:
                    user_name_map[uid] = u["name"]

        shares = _calculate_shares(effective_amount, effective_participant_ids)
        update_fields["participants"] = [
            {
                "user_id": uid,
                "name": user_name_map.get(uid, "Unknown"),
                "share": shares[uid],
            }
            for uid in sorted(effective_participant_ids)
        ]

    if data.note is not None:
        update_fields["note"] = data.note

    await db.expenses.update_one({"_id": eid}, {"$set": update_fields})
    updated_expense = await db.expenses.find_one({"_id": eid})

    # Notify group
    await notify_group_members(
        db=db,
        group=group,
        type="expense_updated",
        message=f"{current_user['name']} updated expense \"{updated_expense['description']}\" "
                f"in \"{group['name']}\".",
        related_entity_id=expense["group_id"],
        related_entity_type="group",
    )

    logger.info("Expense %s updated by user %s", expense_id, user_id)
    return _expense_to_response(updated_expense)


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: str,
    current_user=Depends(get_current_user),
):
    """
    Delete an expense.

    Authorization: any current group member can delete.
    """
    db = get_database()
    user_id = str(current_user["_id"])
    eid = _require_valid_oid(expense_id, "expense ID")

    expense = await db.expenses.find_one({"_id": eid})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    group = await db.groups.find_one({"_id": ObjectId(expense["group_id"])})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Authorization: any current group member can delete
    if user_id not in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of this group to delete expenses.",
        )

    await db.expenses.delete_one({"_id": eid})

    if group:
        await notify_group_members(
            db=db,
            group=group,
            type="expense_deleted",
            message=f"{current_user['name']} deleted the expense \"{expense['description']}\" "
                    f"(₹{expense['amount']:,.2f}) from \"{group['name']}\".",
            related_entity_id=expense["group_id"],
            related_entity_type="group",
        )

    logger.info("Expense %s deleted by user %s", expense_id, user_id)
