"""
AI API route handlers.

Endpoints:
  POST /api/v1/ai/parse-expense — Parse a natural-language expense description

IMPORTANT: This endpoint NEVER writes to the database.
It returns a parsed result that must be confirmed by the user
before being sent to the normal expense creation endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.group import Group, Member
from app.schemas.ai_response import AIParseRequest, AIParseResponse
from app.services.ai.expense_parser import parse_expense_from_text

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/parse-expense", response_model=AIParseResponse)
def parse_expense(
    data: AIParseRequest,
    db: Session = Depends(get_db),
) -> AIParseResponse:
    """
    Parse a natural-language expense description using Gemini AI.

    PIPELINE:
    1. Validate the group exists
    2. Fetch group members for context
    3. Call Gemini API with member context
    4. Validate AI output against group members
    5. Return parsed result for user confirmation

    NOTE: This endpoint NEVER writes to the database.
          The user must confirm the parsed result,
          then the frontend sends it to POST /groups/{id}/expenses.

    On AI failure, returns success=False with a user-friendly error message.
    The frontend should fall back to the manual expense form.
    """
    # Validate group exists
    group = db.get(Group, data.group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id={data.group_id} not found",
        )

    # Fetch actual member names for context and validation
    members = db.execute(
        select(Member).where(Member.group_id == data.group_id)
    ).scalars().all()

    member_names = [m.name for m in members]

    if not member_names:
        return AIParseResponse(
            success=False,
            error="This group has no members. Please add members before using AI expense entry.",
            original_text=data.text,
        )

    # Call the AI service
    result = parse_expense_from_text(
        text=data.text,
        group_member_names=member_names,
        current_member_name=data.current_member_name,
    )

    return result
