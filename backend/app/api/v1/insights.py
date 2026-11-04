"""
Analytics / Insights API routes.

GET  /api/v1/groups/{group_id}/insights   — Group-level analytics
POST /api/v1/groups/{group_id}/insights/ai — AI interpretation of group stats
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.database import get_database
from app.services.balance_engine import calculate_group_balances

router = APIRouter(tags=["insights"])
logger = logging.getLogger(__name__)
settings = get_settings()

EPSILON = 0.005


# ──────────────────────────────────────────────
# Pydantic schemas (local — not in all_schemas to keep changes minimal)
# ──────────────────────────────────────────────

class MonthlyTrendPoint(BaseModel):
    month: str
    total: float


class MemberSpendingItem(BaseModel):
    user_id: str
    name: str
    paid: float
    share: float
    net: float


class GroupInsightsResponse(BaseModel):
    group_id: str
    total_spent: float
    expense_count: int
    avg_expense: float
    max_expense: float
    max_expense_description: str
    user_paid: float
    user_share: float
    user_net_balance: float
    top_spender_name: str
    top_spender_amount: float
    monthly_trend: list[MonthlyTrendPoint]
    member_spending: list[MemberSpendingItem]
    is_settled: bool
    settlement_count: int


class AIInsightRequest(BaseModel):
    stats: dict


class AIInsightResponse(BaseModel):
    success: bool
    summary: str = ""
    insights: list[str] = []
    error: str = ""


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _require_valid_object_id(id_str: str, name: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail=f"Invalid {name}: {id_str!r}")
    return ObjectId(id_str)


async def _get_group_or_404(db, group_id_str: str) -> dict:
    oid = _require_valid_object_id(group_id_str, "group ID")
    group = await db.groups.find_one({"_id": oid})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _require_member(group: dict, user_id: str) -> None:
    if user_id not in group.get("member_ids", []):
        raise HTTPException(status_code=403, detail="Not a member of this group")


def _last_6_months() -> list[str]:
    """Return list of last 6 month strings like 'Sep 2026'."""
    now = datetime.now(timezone.utc)
    months = []
    for i in range(5, -1, -1):
        # Go back i months
        year = now.year
        month = now.month - i
        while month <= 0:
            month += 12
            year -= 1
        dt = datetime(year, month, 1, tzinfo=timezone.utc)
        months.append(dt.strftime("%b %Y"))
    return months


# ──────────────────────────────────────────────
# GET /api/v1/groups/{group_id}/insights
# ──────────────────────────────────────────────

@router.get("/groups/{group_id}/insights", response_model=GroupInsightsResponse)
async def get_group_insights(
    group_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    user_id = str(current_user["_id"])

    # Authorization
    group = await _get_group_or_404(db, group_id)
    _require_member(group, user_id)

    member_ids: list[str] = group.get("member_ids", [])

    # Fetch user names
    member_names: dict[str, str] = {}
    async for u in db.users.find({"_id": {"$in": [ObjectId(uid) for uid in member_ids if ObjectId.is_valid(uid)]}}):
        member_names[str(u["_id"])] = u.get("name", "Unknown")

    # Fetch all expenses
    expenses_list = []
    async for exp in db.expenses.find({"group_id": group_id}):
        expenses_list.append(exp)

    total_spent = sum(float(e.get("amount", 0)) for e in expenses_list)
    expense_count = len(expenses_list)
    avg_expense = round(total_spent / expense_count, 2) if expense_count > 0 else 0.0

    # Max expense
    max_exp = None
    if expenses_list:
        max_exp = max(expenses_list, key=lambda e: float(e.get("amount", 0)))
    max_expense_amount = round(float(max_exp.get("amount", 0)), 2) if max_exp else 0.0
    max_expense_desc = max_exp.get("description", "") if max_exp else ""

    # Monthly trend (last 6 months)
    monthly_totals: dict[str, float] = defaultdict(float)
    for exp in expenses_list:
        dt = exp.get("created_at")
        if isinstance(dt, datetime):
            key = dt.strftime("%b %Y")
            monthly_totals[key] += float(exp.get("amount", 0))

    last_6 = _last_6_months()
    monthly_trend = [
        MonthlyTrendPoint(month=m, total=round(monthly_totals.get(m, 0.0), 2))
        for m in last_6
    ]

    # Calculate balances using existing engine
    balances = await calculate_group_balances(db, group_id, member_ids, member_names)

    # Per-member spending
    member_spending = [
        MemberSpendingItem(
            user_id=uid,
            name=data["member_name"],
            paid=data["total_paid"],
            share=data["total_owed"],
            net=data["net_balance"],
        )
        for uid, data in balances.items()
    ]

    # Top spender
    top_spender_uid = max(balances, key=lambda uid: balances[uid]["total_paid"], default=None)
    top_spender_name = balances[top_spender_uid]["member_name"] if top_spender_uid else ""
    top_spender_amount = balances[top_spender_uid]["total_paid"] if top_spender_uid else 0.0

    # Current user stats
    user_balance = balances.get(user_id, {})
    user_paid = user_balance.get("total_paid", 0.0)
    user_share = user_balance.get("total_owed", 0.0)
    user_net = user_balance.get("net_balance", 0.0)

    # Settlement info
    settlement_count = await db.settlements.count_documents({"group_id": group_id})
    is_settled = all(abs(b["net_balance"]) < EPSILON for b in balances.values())

    return GroupInsightsResponse(
        group_id=group_id,
        total_spent=round(total_spent, 2),
        expense_count=expense_count,
        avg_expense=avg_expense,
        max_expense=max_expense_amount,
        max_expense_description=max_expense_desc,
        user_paid=round(user_paid, 2),
        user_share=round(user_share, 2),
        user_net_balance=round(user_net, 2),
        top_spender_name=top_spender_name,
        top_spender_amount=round(top_spender_amount, 2),
        monthly_trend=monthly_trend,
        member_spending=member_spending,
        is_settled=is_settled,
        settlement_count=settlement_count,
    )


# ──────────────────────────────────────────────
# POST /api/v1/groups/{group_id}/insights/ai
# ──────────────────────────────────────────────

@router.post("/groups/{group_id}/insights/ai", response_model=AIInsightResponse)
async def get_ai_group_insights(
    group_id: str,
    body: AIInsightRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_database),
):
    """
    Interpret validated group statistics using Gemini.
    Stats are provided by the frontend (already fetched from /insights).
    LLM receives only anonymized summary stats — no IDs or auth data.
    """
    user_id = str(current_user["_id"])

    # Authorization
    group = await _get_group_or_404(db, group_id)
    _require_member(group, user_id)

    stats = body.stats

    # Check API key
    if not settings.gemini_api_key or settings.gemini_api_key in ("", "your_gemini_api_key_here"):
        return AIInsightResponse(
            success=False,
            error="AI insights are temporarily unavailable.",
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        # Build prompt with anonymized stats (no user IDs)
        prompt = f"""You are a helpful financial assistant for a group expense app called SplitIt.

Analyze this group's expense statistics and provide concise, friendly insights.

Group Statistics:
- Total group spending: ₹{stats.get('total_spent', 0):.2f}
- Number of expenses: {stats.get('expense_count', 0)}
- Average expense: ₹{stats.get('avg_expense', 0):.2f}
- Largest expense: ₹{stats.get('max_expense', 0):.2f} ({stats.get('max_expense_description', '')})
- Top spender: {stats.get('top_spender_name', 'Unknown')} (paid ₹{stats.get('top_spender_amount', 0):.2f})
- Current user paid: ₹{stats.get('user_paid', 0):.2f}
- Current user's share: ₹{stats.get('user_share', 0):.2f}
- Current user's net balance: ₹{stats.get('user_net_balance', 0):.2f} (positive = owed money, negative = owes money)
- Group is settled: {stats.get('is_settled', False)}
- Number of settlements recorded: {stats.get('settlement_count', 0)}

Respond with ONLY valid JSON (no markdown, no explanation outside JSON):
{{
  "summary": "One friendly sentence summarizing the group's financial situation.",
  "insights": [
    "Insight 1 (max 15 words)",
    "Insight 2 (max 15 words)",
    "Insight 3 (max 15 words)"
  ]
}}

Rules:
- Be encouraging and friendly
- Use ₹ for Indian rupees
- Keep each insight concise (under 15 words)
- Do NOT invent numbers — only use the stats provided
- If group has no expenses, say so in summary"""

        # Run in a shared thread-pool executor so the event loop is never blocked.
        # 25-second timeout matches the frontend insightsApi.getAIInsights timeout.
        from app.api.v1.ai import _gemini_executor
        loop = asyncio.get_event_loop()
        gen_future = loop.run_in_executor(_gemini_executor, model.generate_content, prompt)
        try:
            response = await asyncio.wait_for(gen_future, timeout=25.0)
        except asyncio.TimeoutError:
            raise Exception('Gemini API timed out after 25 seconds')
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        return AIInsightResponse(
            success=True,
            summary=str(parsed.get("summary", "")),
            insights=[str(i) for i in parsed.get("insights", [])[:5]],
        )

    except json.JSONDecodeError as e:
        logger.warning("AI insights: JSON parse failed: %s", e)
        return AIInsightResponse(
            success=False,
            error="AI insights are temporarily unavailable.",
        )
    except Exception as e:
        logger.error("AI insights failed: %s", e, exc_info=True)
        return AIInsightResponse(
            success=False,
            error="AI insights are temporarily unavailable.",
        )
