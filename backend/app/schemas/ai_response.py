"""
Pydantic schemas for AI expense parsing request/response.
"""

from decimal import Decimal
from pydantic import BaseModel, Field


class AIParseRequest(BaseModel):
    """Request to parse a natural-language expense description."""
    text: str = Field(..., min_length=1, max_length=2000, description="Natural language expense description")
    group_id: int = Field(..., description="Group ID to validate member names against")
    current_member_name: str | None = Field(
        None,
        description="Name of the member entering the expense (for pronoun resolution like 'I', 'me')"
    )


class AIParseResult(BaseModel):
    """
    Structured expense data extracted by AI.
    
    IMPORTANT: This is the OUTPUT of the AI service.
    It is NEVER written directly to the database.
    It must be confirmed by the user and then passed through
    the normal expense creation pipeline.
    """
    description: str | None = Field(None, description="Expense description")
    amount: Decimal | None = Field(None, description="Total expense amount")
    payer_name: str | None = Field(None, description="Name of who paid")
    participant_names: list[str] = Field(default_factory=list, description="Names of participants")
    confidence: str = Field("high", description="AI confidence: high, medium, low")
    notes: str | None = Field(None, description="Any ambiguities or notes from AI")


class AIParseResponse(BaseModel):
    """
    Response from the AI parse endpoint.
    
    Includes the parsed result plus validation info.
    The result is NOT yet saved — user must confirm.
    """
    success: bool
    result: AIParseResult | None = None
    # Validation issues found (e.g., unknown member names)
    warnings: list[str] = Field(default_factory=list)
    # If success=False, the error message
    error: str | None = None
    # The original input text (for display in confirmation UI)
    original_text: str = ""
