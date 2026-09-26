"""
Dashboard API route.

GET /api/v1/dashboard — Real statistics for the current user.
"""

import logging
from fastapi import APIRouter, Depends
from bson import ObjectId

from app.core.auth import get_current_user
from app.db.database import get_database
from app.schemas.all_schemas import DashboardResponse, ExpenseParticipantResponse, ExpenseResponse, GroupListItem
from app.services.balance_engine import calculate_group_balances

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(current_user=Depends(get_current_user)):
    """
    Get dashboard statistics for the authenticated user.
    All values are computed from real database data.
    """
    db = get_database()
    user_id = str(current_user["_id"])

    # 1. Get all the user's groups
    groups = await db.groups.find(
        {"member_ids": user_id},
        sort=[("created_at", -1)],
    ).to_list(100)

    # 2. Compute balances across all groups
    total_you_owe = 0.0
    total_you_are_owed = 0.0

    for group in groups:
        group_id = str(group["_id"])
        member_ids = group.get("member_ids", [])

        member_names: dict[str, str] = {}
        for uid in member_ids:
            if ObjectId.is_valid(uid):
                u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
                if u:
                    member_names[uid] = u["name"]

        balances = await calculate_group_balances(
            db=db,
            group_id=group_id,
            member_ids=member_ids,
            member_names=member_names,
        )

        if user_id in balances:
            net = balances[user_id]["net_balance"]
            if net > 0:
                total_you_are_owed += net
            elif net < 0:
                total_you_owe += abs(net)

    # 3. Recent expenses across all user's groups (last 10)
    group_ids = [str(g["_id"]) for g in groups]
    recent_expenses_raw = await db.expenses.find(
        {"group_id": {"$in": group_ids}},
        sort=[("created_at", -1)],
        limit=10,
    ).to_list(10)

    recent_expenses = [
        ExpenseResponse(
            id=str(e["_id"]),
            group_id=e["group_id"],
            description=e["description"],
            amount=e["amount"],
            payer_id=e["payer_id"],
            payer_name=e["payer_name"],
            participants=[
                ExpenseParticipantResponse(**p)
                for p in e.get("participants", [])
            ],
            note=e.get("note"),
            created_by=e["created_by"],
            created_at=e["created_at"],
            updated_at=e["updated_at"],
        )
        for e in recent_expenses_raw
    ]

    # 4. Group list items
    group_items = [
        GroupListItem(
            id=str(g["_id"]),
            name=g["name"],
            description=g.get("description"),
            member_count=len(g.get("member_ids", [])),
            created_at=g["created_at"],
        )
        for g in groups[:5]  # Show top 5 recent groups on dashboard
    ]

    return DashboardResponse(
        total_groups=len(groups),
        you_owe=round(total_you_owe, 2),
        you_are_owed=round(total_you_are_owed, 2),
        net_balance=round(total_you_are_owed - total_you_owe, 2),
        recent_expenses=recent_expenses,
        groups=group_items,
    )
