"""
Pydantic schemas for Expense API request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator


# ===========================
# Expense Schemas
# ===========================

class ExpenseParticipantResponse(BaseModel):
    """Participant in an expense with their share."""
    model_config = {"from_attributes": True}

    id: int
    member_id: int
    member_name: str = ""  # populated by service
    share: Decimal


class ExpenseCreate(BaseModel):
    """Schema for creating a new expense."""
    description: str = Field(..., min_length=1, max_length=500)
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    payer_id: int = Field(..., description="Member ID of who paid")
    participant_ids: list[int] = Field(..., min_length=1, description="Member IDs of participants")
    note: str | None = Field(None, max_length=1000)

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be blank")
        return v.strip()

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v

    @field_validator("participant_ids")
    @classmethod
    def participants_must_be_unique(cls, v: list[int]) -> list[int]:
        if len(v) != len(set(v)):
            raise ValueError("Participant IDs must be unique")
        return v

    @model_validator(mode="after")
    def payer_must_be_participant(self) -> "ExpenseCreate":
        """Payer is not required to be a participant (they can pay for others)."""
        return self


class ExpenseResponse(BaseModel):
    """Schema for returning expense data."""
    model_config = {"from_attributes": True}

    id: int
    group_id: int
    description: str
    amount: Decimal
    payer_id: int
    payer_name: str = ""  # populated by service
    note: str | None
    created_at: datetime
    participants: list[ExpenseParticipantResponse] = []
