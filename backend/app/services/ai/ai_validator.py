"""
AI output validator.

After the LLM returns a parsed expense, this module validates:
1. Schema correctness (handled by Pydantic)
2. Member names exist in the group
3. Amount is valid
4. No unknown members

This is the application-level validation layer between AI output and the normal expense pipeline.
"""

from decimal import Decimal
from app.schemas.ai_response import AIParseResult


def validate_ai_parse_result(
    result: AIParseResult,
    group_member_names: list[str],
) -> tuple[AIParseResult, list[str]]:
    """
    Validate AI parse result against group members and business rules.

    Returns:
        (validated_result, warnings)
        - validated_result: The result with any invalid member names removed/flagged
        - warnings: List of warning messages for the user
    """
    warnings: list[str] = []

    # Normalize names for case-insensitive comparison
    valid_names_lower = {name.lower(): name for name in group_member_names}

    # Validate payer
    corrected_payer = result.payer_name
    if result.payer_name is not None:
        payer_lower = result.payer_name.strip().lower()
        if payer_lower in valid_names_lower:
            # Correct the casing to match the actual member name
            corrected_payer = valid_names_lower[payer_lower]
        else:
            warnings.append(
                f"AI suggested payer '{result.payer_name}' who is not in this group. "
                f"Please select the correct payer."
            )
            corrected_payer = None

    # Validate participants
    validated_participants: list[str] = []
    for name in result.participant_names:
        name_lower = name.strip().lower()
        if name_lower in valid_names_lower:
            validated_participants.append(valid_names_lower[name_lower])
        else:
            warnings.append(
                f"AI suggested participant '{name}' who is not in this group and was removed."
            )

    # Validate amount
    if result.amount is not None:
        try:
            amount = Decimal(str(result.amount))
            if amount <= 0:
                warnings.append("AI extracted a non-positive amount. Please enter the amount manually.")
                result = result.model_copy(update={"amount": None})
        except Exception:
            warnings.append("AI extracted an invalid amount. Please enter the amount manually.")
            result = result.model_copy(update={"amount": None})

    # Build corrected result
    corrected_result = result.model_copy(update={
        "payer_name": corrected_payer,
        "participant_names": validated_participants,
    })

    # Set confidence to low if many warnings
    if len(warnings) >= 2:
        corrected_result = corrected_result.model_copy(update={"confidence": "low"})

    return corrected_result, warnings
