"""
Dashboard API route.

GET /api/v1/dashboard — Real statistics for the current user.

Performance notes:
- Member names are batch-fetched with a single $in query per group instead of
  per-member queries (eliminates N+1 pattern).
- Groups, recent expenses, and member lookups are structured to minimise
  round trips.
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

    # 2. Collect ALL unique member IDs across all groups, then fetch names once.
    #    This replaces the previous per-member per-group loop (N+1 pattern).
    all_member_id_strs: set[str] = set()
    for group in groups:
        for uid in group.get("member_ids", []):
            if ObjectId.is_valid(uid):
                all_member_id_strs.add(uid)

    # Single batch query for all member names
    all_member_names: dict[str, str] = {}
    if all_member_id_strs:
        async for u in db.users.find(
            {"_id": {"$in": [ObjectId(uid) for uid in all_member_id_strs]}},
            {"name": 1},
        ):
            all_member_names[str(u["_id"])] = u.get("name", "Unknown")

    # 3. Compute balances across all groups (uses batch-fetched names — no extra DB calls)
    total_you_owe = 0.0
    total_you_are_owed = 0.0
    group_net_balances: dict[str, float] = {}  # group_id → user net balance

    for group in groups:
        group_id = str(group["_id"])
        member_ids = group.get("member_ids", [])

        # Build member_names subset for this group from the already-fetched map
        member_names = {uid: all_member_names.get(uid, "Unknown") for uid in member_ids}

        try:
            balances = await calculate_group_balances(
                db=db,
                group_id=group_id,
                member_ids=member_ids,
                member_names=member_names,
            )

            if user_id in balances:
                net = balances[user_id]["net_balance"]
                group_net_balances[group_id] = net
                if net > 0:
                    total_you_are_owed += net
                elif net < 0:
                    total_you_owe += abs(net)
        except Exception as e:
            logger.warning("Balance calculation failed for group %s: %s", group_id, e)

    # 4. Recent expenses across all user's groups (last 10)
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

    # 5. Group list items — include per-group net balance
    group_items = [
        GroupListItem(
            id=str(g["_id"]),
            name=g["name"],
            description=g.get("description"),
            member_count=len(g.get("member_ids", [])),
            created_at=g["created_at"],
            user_net_balance=group_net_balances.get(str(g["_id"])),
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
