"""
Expense Parser — AI service that parses natural-language expense descriptions.

PIPELINE:
1. Receive text + group context
2. Build controlled prompt
3. Call Gemini API
4. Parse response as JSON
5. Validate with Pydantic schema
6. Validate member names against actual group
7. Return structured result (NEVER write to DB)

GUARDRAILS:
- LLM output is NEVER written to the database
- Member names are validated against actual group members
- Amounts must be positive numbers
- All financial calculations happen in expense_calculator.py, not here
"""

import json
import logging
from decimal import Decimal, InvalidOperation

import google.generativeai as genai

from app.core.config import get_settings
from app.schemas.ai_response import AIParseResult, AIParseResponse
from app.services.ai.prompt_builder import (
    EXPENSE_PARSE_SYSTEM_PROMPT,
    build_expense_parse_prompt,
)
from app.services.ai.ai_validator import validate_ai_parse_result

logger = logging.getLogger(__name__)
settings = get_settings()


def _parse_gemini_response(response_text: str) -> AIParseResult:
    """
    Parse the raw Gemini response text into an AIParseResult.

    Handles common issues: markdown code fences, extra whitespace, etc.

    Raises:
        ValueError: If the response is not valid JSON or doesn't match schema.
    """
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"AI returned invalid JSON: {e}") from e

    # Convert amount to Decimal if present
    if data.get("amount") is not None:
        try:
            data["amount"] = Decimal(str(data["amount"]))
        except (InvalidOperation, TypeError):
            data["amount"] = None

    # Normalize participants field name (model might use 'participants' or 'participant_names')
    if "participants" in data and "participant_names" not in data:
        data["participant_names"] = data.pop("participants")

    # Handle 'payer' vs 'payer_name'
    if "payer" in data and "payer_name" not in data:
        data["payer_name"] = data.pop("payer")

    return AIParseResult(**{k: v for k, v in data.items() if k in AIParseResult.model_fields})


def parse_expense_from_text(
    text: str,
    group_member_names: list[str],
    current_member_name: str | None = None,
) -> AIParseResponse:
    """
    Main entry point: parse a natural-language expense description.

    Args:
        text: User's natural language input.
        group_member_names: Actual member names in the group (for validation).
        current_member_name: Name to use for pronoun resolution ('I', 'me').

    Returns:
        AIParseResponse with success status, parsed result, and any warnings.
        On failure, returns success=False with an error message.

    NOTE: This function NEVER writes to the database.
          The result must be confirmed by the user before being sent to
          the normal expense creation endpoint.
    """
    # Check API key is configured
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        logger.warning("Gemini API key not configured")
        return AIParseResponse(
            success=False,
            error="AI service is not configured. Please use the manual expense form.",
            original_text=text,
        )

    try:
        # Configure the Gemini client
        genai.configure(api_key=settings.gemini_api_key)

        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=EXPENSE_PARSE_SYSTEM_PROMPT,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Low temperature for deterministic parsing
                response_mime_type="application/json",
            ),
        )

        # Build the user prompt with group context
        prompt = build_expense_parse_prompt(
            text=text,
            member_names=group_member_names,
            current_member_name=current_member_name,
        )

        logger.info("Calling Gemini API for expense parsing")
        response = model.generate_content(prompt)

        if not response.text:
            return AIParseResponse(
                success=False,
                error="AI returned an empty response. Please try again or use manual entry.",
                original_text=text,
            )

        # Parse the response
        raw_result = _parse_gemini_response(response.text)

        # Validate against group members
        validated_result, warnings = validate_ai_parse_result(
            result=raw_result,
            group_member_names=group_member_names,
        )

        logger.info(
            "Expense parsed successfully: description=%s amount=%s confidence=%s",
            validated_result.description,
            validated_result.amount,
            validated_result.confidence,
        )

        return AIParseResponse(
            success=True,
            result=validated_result,
            warnings=warnings,
            original_text=text,
        )

    except ValueError as e:
        logger.warning("Failed to parse AI response: %s", e)
        return AIParseResponse(
            success=False,
            error=f"Could not understand the AI response: {e}. Please use manual entry.",
            original_text=text,
        )
    except Exception as e:
        logger.error("Gemini API error: %s", e, exc_info=True)
        return AIParseResponse(
            success=False,
            error="AI service is temporarily unavailable. Please use the manual expense form.",
            original_text=text,
        )
