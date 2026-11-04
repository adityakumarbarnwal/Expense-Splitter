"""
AI expense parsing route — MongoDB backend.

POST /api/v1/groups/:id/expenses/parse-ai

IMPORTANT: This endpoint NEVER writes to MongoDB.
The parsed result must be confirmed by the user before being sent to the
normal expense creation endpoint.

ASYNC DESIGN:
  google.generativeai SDK 0.x uses a synchronous blocking HTTP client.
  Calling model.generate_content() directly inside an async FastAPI handler
  blocks the entire event loop for the duration of the Gemini round-trip
  (typically 1-5 seconds, but up to 30+ seconds on slow models or cold starts).
  This is the root cause of the "timeout of 30000ms exceeded" frontend error.

  FIX: Wrap the synchronous SDK call in asyncio.get_event_loop().run_in_executor()
  with a dedicated ThreadPoolExecutor so the event loop stays free.
  A 25-second asyncio.wait_for() timeout surfaces Gemini latency clearly.
"""

import asyncio
import concurrent.futures
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.database import get_database, retry_db_read
from app.schemas.all_schemas import AIParseRequest, AIParseResponse, AIParseResult

router = APIRouter(tags=["ai"])
logger = logging.getLogger(__name__)
settings = get_settings()

# Reuse a module-level executor to avoid spawning threads per request
_gemini_executor = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="gemini")


def _call_gemini_sync(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Synchronous Gemini call — MUST run in a thread, not the event loop.

    Returns the raw response text.
    Raises on API errors (invalid model, auth failure, quota, network, etc.)
    """
    import google.generativeai as genai  # import inside thread is fine — module cached

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,          # Low temperature → deterministic JSON
            response_mime_type="application/json",
        ),
    )
    response = model.generate_content(user_prompt)
    if not response.text:
        raise ValueError("Gemini returned an empty response")
    return response.text


async def _parse_with_gemini(
    text: str,
    member_names: list[str],
    current_user_name: str | None,
) -> AIParseResponse:
    """
    Call Gemini API asynchronously and parse the structured response.

    All errors are logged with full detail and returned as user-friendly messages.
    Never exposes API key, internal stack traces, or raw Gemini error text to callers.
    """
    # ── API key guard ──────────────────────────────────────────────────────
    if not settings.gemini_api_key or settings.gemini_api_key in ("", "your_gemini_api_key_here"):
        logger.error("GEMINI_API_KEY is not configured in .env")
        return AIParseResponse(
            success=False,
            error="AI service is not configured. Please use the manual expense form.",
            original_text=text,
        )

    # ── Build prompts ──────────────────────────────────────────────────────
    system_prompt = (
        "You are an expense parsing assistant for a group expense splitting app. "
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
        + (f"Current user (resolve 'I', 'me', 'my' to this name): {current_user_name}\n" if current_user_name else "")
    )

    user_prompt = f"Parse this expense: {text}"

    # ── Call Gemini in a thread (non-blocking) ─────────────────────────────
    logger.info(
        "Calling Gemini API (%s) for expense parsing (async via executor)",
        settings.gemini_model,
    )
    loop = asyncio.get_event_loop()
    try:
        raw_text = await asyncio.wait_for(
            loop.run_in_executor(
                _gemini_executor,
                _call_gemini_sync,
                settings.gemini_api_key,
                settings.gemini_model,
                system_prompt,
                user_prompt,
            ),
            timeout=25.0,  # Surface Gemini latency; 25s > typical 1-5s response
        )
    except asyncio.TimeoutError:
        logger.error("Gemini API timed out after 25 seconds (model=%s)", settings.gemini_model)
        return AIParseResponse(
            success=False,
            error="AI service took too long to respond. Please try again or use manual entry.",
            original_text=text,
        )
    except Exception as exc:
        # Classify the error without leaking credentials
        exc_str = str(exc)
        if "404" in exc_str or "not found" in exc_str.lower() or "no longer available" in exc_str.lower():
            logger.error(
                "Gemini model '%s' is unavailable: %s", settings.gemini_model, exc_str
            )
            return AIParseResponse(
                success=False,
                error=f"AI model '{settings.gemini_model}' is not available. "
                      "Update GEMINI_MODEL in backend/.env to a supported model (e.g. gemini-2.5-flash).",
                original_text=text,
            )
        if "INVALID_ARGUMENT" in exc_str or "API key" in exc_str:
            logger.error("Gemini API key error: %s", exc_str)
            return AIParseResponse(
                success=False,
                error="AI service configuration error. Please contact the administrator.",
                original_text=text,
            )
        if "quota" in exc_str.lower() or "rate" in exc_str.lower() or "429" in exc_str:
            logger.warning("Gemini quota/rate limit hit: %s", exc_str)
            return AIParseResponse(
                success=False,
                error="AI service is currently rate-limited. Please wait a moment and try again.",
                original_text=text,
            )
        logger.error("Gemini API error: %s", exc, exc_info=True)
        return AIParseResponse(
            success=False,
            error="AI service is temporarily unavailable. Please use the manual expense form.",
            original_text=text,
        )

    # ── Parse JSON response ─────────────────────────────────────────────────
    response_text = raw_text.strip()

    # Strip markdown code fences if the model adds them despite the mime type setting
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        inner, in_block = [], False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                break
            elif in_block:
                inner.append(line)
        response_text = "\n".join(inner).strip()

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as exc:
        logger.error(
            "Gemini response was not valid JSON: %s | response preview: %.200s",
            exc, response_text,
        )
        return AIParseResponse(
            success=False,
            error="AI returned malformed data. Please try again or use manual entry.",
            original_text=text,
        )

    # ── Validate member names (case-insensitive) ───────────────────────────
    member_names_lower = {n.lower(): n for n in member_names}
    warnings: list[str] = []

    payer_name = data.get("payer_name")
    if payer_name and payer_name.lower() not in member_names_lower:
        warnings.append(
            f"AI suggested payer '{payer_name}' who is not in this group. "
            "Please select the payer manually."
        )
        payer_name = None
    elif payer_name:
        payer_name = member_names_lower[payer_name.lower()]

    raw_participants = data.get("participant_names") or []
    valid_participants: list[str] = []
    for name in raw_participants:
        if name and name.lower() in member_names_lower:
            valid_participants.append(member_names_lower[name.lower()])
        elif name:
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
    The Gemini SDK call runs in a thread pool — does NOT block the event loop.
    """
    db = get_database()
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(group_id):
        raise HTTPException(status_code=400, detail="Invalid group ID")

    group = await retry_db_read(
        lambda: db.groups.find_one({"_id": ObjectId(group_id)})
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if user_id not in group.get("member_ids", []):
        raise HTTPException(status_code=403, detail="You are not a member of this group.")

    # Batch-fetch member names (one query, not N queries)
    member_ids = group.get("member_ids", [])
    valid_oids = [ObjectId(uid) for uid in member_ids if ObjectId.is_valid(uid)]
    member_names: list[str] = []
    if valid_oids:
        async for u in db.users.find({"_id": {"$in": valid_oids}}, {"name": 1}):
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
