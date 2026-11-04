"""
Balances and Settlements API routes — MongoDB backend.

Routes:
  GET   /api/v1/groups/:id/balances             — Get net balances + suggestions
  GET   /api/v1/groups/:id/settlements          — List settlements
  POST  /api/v1/groups/:id/settlements          — Record a settlement
  PATCH /api/v1/settlements/:id                 — Edit a settlement (any member)
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.auth import get_current_user
from app.db.database import get_database
from app.models.documents import SettlementDocument
from app.schemas.all_schemas import (
    CreateSettlementRequest,
    GroupBalancesResponse,
    MemberBalanceResponse,
    SettlementResponse,
    SettlementSuggestion,
    UpdateSettlementRequest,
)
from app.services.balance_engine import calculate_group_balances, generate_settlement_suggestions
from app.services.notification_service import notify_group_members

router = APIRouter(tags=["balances"])
logger = logging.getLogger(__name__)


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


async def _build_member_name_map(db, member_ids: list[str]) -> dict[str, str]:
    name_map: dict[str, str] = {}
    for uid in member_ids:
        if ObjectId.is_valid(uid):
            u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
            if u:
                name_map[uid] = u["name"]
    return name_map


@router.get("/groups/{group_id}/balances", response_model=GroupBalancesResponse)
async def get_balances(
    group_id: str,
    current_user=Depends(get_current_user),
):
    """Get net balances for all group members and settlement suggestions."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    member_ids = group.get("member_ids", [])
    member_names = await _build_member_name_map(db, member_ids)

    raw_balances = await calculate_group_balances(
        db=db,
        group_id=group_id,
        member_ids=member_ids,
        member_names=member_names,
    )

    balances = [
        MemberBalanceResponse(**data)
        for data in raw_balances.values()
    ]

    suggestions_raw = generate_settlement_suggestions(raw_balances)
    suggestions = [SettlementSuggestion(**s) for s in suggestions_raw]

    is_settled = all(abs(b.net_balance) < 0.005 for b in balances)

    return GroupBalancesResponse(
        group_id=group_id,
        balances=balances,
        settlement_suggestions=suggestions,
        is_settled=is_settled,
    )


@router.get("/groups/{group_id}/settlements", response_model=list[SettlementResponse])
async def list_settlements(
    group_id: str,
    current_user=Depends(get_current_user),
):
    """List all settlements for a group."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    settlements = await db.settlements.find(
        {"group_id": group_id},
        sort=[("created_at", -1)],
    ).to_list(500)

    return [
        SettlementResponse(
            id=str(s["_id"]),
            group_id=s["group_id"],
            payer_id=s["payer_id"],
            payer_name=s["payer_name"],
            receiver_id=s["receiver_id"],
            receiver_name=s["receiver_name"],
            amount=s["amount"],
            note=s.get("note"),
            created_at=s["created_at"],
            updated_at=s.get("updated_at"),
        )
        for s in settlements
    ]


@router.post("/groups/{group_id}/settlements", response_model=SettlementResponse, status_code=201)
async def record_settlement(
    group_id: str,
    data: CreateSettlementRequest,
    current_user=Depends(get_current_user),
):
    """Record a debt settlement between two group members."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    member_ids = group.get("member_ids", [])

    if data.payer_id not in member_ids:
        raise HTTPException(status_code=400, detail="Payer is not a group member.")
    if data.receiver_id not in member_ids:
        raise HTTPException(status_code=400, detail="Receiver is not a group member.")

    # Fetch user names
    payer_user = await db.users.find_one({"_id": ObjectId(data.payer_id)}, {"name": 1}) if ObjectId.is_valid(data.payer_id) else None
    receiver_user = await db.users.find_one({"_id": ObjectId(data.receiver_id)}, {"name": 1}) if ObjectId.is_valid(data.receiver_id) else None

    if not payer_user or not receiver_user:
        raise HTTPException(status_code=404, detail="Could not find payer or receiver user.")

    settlement_doc = SettlementDocument(
        group_id=group_id,
        payer_id=data.payer_id,
        payer_name=payer_user["name"],
        receiver_id=data.receiver_id,
        receiver_name=receiver_user["name"],
        amount=data.amount,
        note=data.note,
        created_by=user_id,
    )

    result = await db.settlements.insert_one(settlement_doc.to_dict())
    settlement = await db.settlements.find_one({"_id": result.inserted_id})

    await notify_group_members(
        db=db,
        group=group,
        type="settlement_recorded",
        message=f"{payer_user['name']} paid ₹{data.amount:,.2f} to "
                f"{receiver_user['name']} in \"{group['name']}\".",
        related_entity_id=group_id,
        related_entity_type="group",
    )

    return SettlementResponse(
        id=str(settlement["_id"]),
        group_id=settlement["group_id"],
        payer_id=settlement["payer_id"],
        payer_name=settlement["payer_name"],
        receiver_id=settlement["receiver_id"],
        receiver_name=settlement["receiver_name"],
        amount=settlement["amount"],
        note=settlement.get("note"),
        created_at=settlement["created_at"],
        updated_at=settlement.get("updated_at"),
    )


@router.patch("/settlements/{settlement_id}", response_model=SettlementResponse)
async def update_settlement(
    settlement_id: str,
    data: UpdateSettlementRequest,
    current_user=Depends(get_current_user),
):
    """
    Update an existing settlement.

    Authorization: any current group member can update a settlement.
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # 2. Validate settlement_id as ObjectId
    sid = _require_valid_oid(settlement_id, "settlement ID")

    # 3. Fetch settlement
    settlement = await db.settlements.find_one({"_id": sid})
    if not settlement:
        raise HTTPException(status_code=404, detail="Settlement not found")

    # 4. Fetch group by settlement["group_id"]
    group = await _get_group_or_404(db, settlement["group_id"])

    # 5. Check user is a group member — raise 403 if not
    await _require_member(group, user_id)

    member_ids = group.get("member_ids", [])

    # Effective payer and receiver
    effective_payer_id = data.payer_id if data.payer_id is not None else settlement["payer_id"]
    effective_receiver_id = data.receiver_id if data.receiver_id is not None else settlement["receiver_id"]

    # 6. Validate any new payer_id or receiver_id are group members
    if data.payer_id is not None and data.payer_id not in member_ids:
        raise HTTPException(status_code=400, detail="Payer is not a group member.")
    if data.receiver_id is not None and data.receiver_id not in member_ids:
        raise HTTPException(status_code=400, detail="Receiver is not a group member.")

    # 7. Prevent payer_id == receiver_id
    if effective_payer_id == effective_receiver_id:
        raise HTTPException(status_code=400, detail="Payer and receiver must be different.")

    # 8. Lookup new names from db.users if ids change
    # 9. Build update_fields with only changed fields + updated_at: datetime.now(timezone.utc)
    now = datetime.now(timezone.utc)
    update_fields: dict = {"updated_at": now}

    if data.payer_id is not None:
        payer_user = await db.users.find_one({"_id": ObjectId(data.payer_id)}, {"name": 1}) if ObjectId.is_valid(data.payer_id) else None
        if not payer_user:
            raise HTTPException(status_code=404, detail="Payer user not found.")
        update_fields["payer_id"] = data.payer_id
        update_fields["payer_name"] = payer_user["name"]

    if data.receiver_id is not None:
        receiver_user = await db.users.find_one({"_id": ObjectId(data.receiver_id)}, {"name": 1}) if ObjectId.is_valid(data.receiver_id) else None
        if not receiver_user:
            raise HTTPException(status_code=404, detail="Receiver user not found.")
        update_fields["receiver_id"] = data.receiver_id
        update_fields["receiver_name"] = receiver_user["name"]

    if data.amount is not None:
        update_fields["amount"] = data.amount

    if data.note is not None:
        update_fields["note"] = data.note

    # 10. Apply update
    await db.settlements.update_one({"_id": sid}, {"$set": update_fields})

    # 11. Fetch updated settlement
    updated_settlement = await db.settlements.find_one({"_id": sid})

    # 12. Send ONE notification to group:
    new_amount = updated_settlement["amount"]
    await notify_group_members(
        db=db,
        group=group,
        type="settlement_updated",
        message=f"{current_user['name']} updated a settlement of ₹{new_amount:,.2f} in \"{group['name']}\".",
        related_entity_id=settlement["group_id"],
        related_entity_type="group",
    )

    logger.info("Settlement %s updated by user %s", settlement_id, user_id)

    # 13. Return SettlementResponse
    return SettlementResponse(
        id=str(updated_settlement["_id"]),
        group_id=updated_settlement["group_id"],
        payer_id=updated_settlement["payer_id"],
        payer_name=updated_settlement["payer_name"],
        receiver_id=updated_settlement["receiver_id"],
        receiver_name=updated_settlement["receiver_name"],
        amount=updated_settlement["amount"],
        note=updated_settlement.get("note"),
        created_at=updated_settlement["created_at"],
        updated_at=updated_settlement.get("updated_at"),
    )

