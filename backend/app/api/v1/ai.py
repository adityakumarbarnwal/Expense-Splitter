"""
AI expense parsing route — MongoDB backend.

POST /api/v1/groups/:id/expenses/parse-ai

IMPORTANT: This endpoint NEVER writes to MongoDB.
The parsed result must be confirmed by the user before being sent to the
normal expense creation endpoint.
"""

import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.database import get_database
from app.schemas.all_schemas import AIParseRequest, AIParseResponse, AIParseResult

router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)
settings = get_settings()


async def _parse_with_gemini(
    text: str,
    member_names: list[str],
    current_user_name: str | None,
) -> AIParseResponse:
    """
    Call Gemini API and parse the response.

    All errors are logged with full detail and returned as user-friendly messages.
    """
    # ──────────────────────────────────────────────
    # Check API key
    # ──────────────────────────────────────────────
    if not settings.gemini_api_key or settings.gemini_api_key in ("", "your_gemini_api_key_here"):
        logger.error("GEMINI_API_KEY is not configured in .env")
        return AIParseResponse(
            success=False,
            error="AI service is not configured (missing API key). Please use the manual expense form.",
            original_text=text,
        )

    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)

        # System prompt
        system_prompt = (
            "You are an expense parsing assistant. "
            "Extract expense information from the user's text and return ONLY valid JSON. "
            "Do not include any explanation, markdown, or code fences.\n\n"
            "Return this exact JSON structure:\n"
            "{\n"
            '  "description": "short expense description (2-5 words)",\n'
            '  "amount": <number or null if not clear>,\n'
            '  "payer_name": "name of who paid (or null)",\n'
            '  "participant_names": ["list", "of", "participant", "names"],\n'
            '  "confidence": "high|medium|low",\n'
            '  "notes": "any ambiguity notes or null"\n'
            "}\n\n"
            f"Group members: {', '.join(member_names)}\n"
            + (f"Current user (resolve 'I', 'me' to this name): {current_user_name}\n" if current_user_name else "")
        )

        user_prompt = f"Parse this expense: {text}"

        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=system_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )

        logger.info("Calling Gemini API (%s) for expense parsing", settings.gemini_model)
        response = model.generate_content(user_prompt)

        if not response.text:
            logger.error("Gemini returned empty response")
            return AIParseResponse(
                success=False,
                error="AI returned an empty response. Please try again or use manual entry.",
                original_text=text,
            )

        response_text = response.text.strip()
        # Strip markdown fences if model adds them despite the mime type setting
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            inner = []
            in_block = False
            for line in lines:
                if line.startswith("```") and not in_block:
                    in_block = True
                    continue
                elif line.startswith("```") and in_block:
                    break
                elif in_block:
                    inner.append(line)
            response_text = "\n".join(inner)

        data = json.loads(response_text)

        # Validate member names (case-insensitive)
        member_names_lower = {n.lower(): n for n in member_names}
        warnings: list[str] = []

        payer_name = data.get("payer_name")
        if payer_name and payer_name.lower() not in member_names_lower:
            warnings.append(
                f"AI suggested payer '{payer_name}' who is not in this group. Please select the payer manually."
            )
            payer_name = None
        elif payer_name:
            payer_name = member_names_lower[payer_name.lower()]

        raw_participants = data.get("participant_names", [])
        valid_participants = []
        for name in raw_participants:
            if name.lower() in member_names_lower:
                valid_participants.append(member_names_lower[name.lower()])
            else:
                warnings.append(f"'{name}' is not a group member and was removed from participants.")

        amount = data.get("amount")
        if amount is not None:
            try:
                amount = float(amount)
                if amount <= 0:
                    warnings.append("AI returned a non-positive amount. Please enter the amount manually.")
                    amount = None
            except (ValueError, TypeError):
                amount = None

        result = AIParseResult(
            description=data.get("description"),
            amount=amount,
            payer_name=payer_name,
            participant_names=valid_participants,
            confidence=data.get("confidence", "low"),
            notes=data.get("notes"),
        )

        logger.info(
            "AI parse successful: desc=%s amount=%s confidence=%s warnings=%d",
            result.description, result.amount, result.confidence, len(warnings),
        )

        return AIParseResponse(
            success=True,
            result=result,
            warnings=warnings,
            original_text=text,
        )

    except json.JSONDecodeError as e:
        logger.error("Gemini response was not valid JSON: %s | response: %s", e, response_text if 'response_text' in dir() else 'N/A')
        return AIParseResponse(
            success=False,
            error=f"AI returned malformed data. Please use the manual form. (JSON error: {e})",
            original_text=text,
        )
    except Exception as e:
        logger.error("Gemini API error: %s", e, exc_info=True)
        return AIParseResponse(
            success=False,
            error=f"AI service error: {type(e).__name__}. Check backend logs. Please use the manual form.",
            original_text=text,
        )


@router.post("/groups/{group_id}/expenses/parse-ai", response_model=AIParseResponse)
async def parse_expense_ai(
    group_id: str,
    data: AIParseRequest,
    current_user=Depends(get_current_user),
):
    """
    Parse a natural-language expense description using Gemini AI.

    NEVER writes to the database.
    Returns parsed result for user confirmation before saving.
    """
    db = get_database()
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=400, detail="Invalid group ID")

    group = await db.groups.find_one({"_id": ObjectId(group_id)})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if user_id not in group.get("member_ids", []):
        raise HTTPException(status_code=403, detail="You are not a member of this group.")

    # Get member names
    member_names: list[str] = []
    for uid in group.get("member_ids", []):
        if ObjectId.is_valid(uid):
            u = await db.users.find_one({"_id": ObjectId(uid)}, {"name": 1})
            if u:
                member_names.append(u["name"])

    if not member_names:
        return AIParseResponse(
            success=False,
            error="This group has no members. Add members before using AI entry.",
            original_text=data.text,
        )

    return await _parse_with_gemini(
        text=data.text,
        member_names=member_names,
        current_user_name=data.current_user_name or current_user.get("name"),
    )
