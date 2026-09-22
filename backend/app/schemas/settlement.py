"""
Pydantic schemas for Settlement API request/response validation.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator


class SettlementCreate(BaseModel):
    """Schema for recording a settlement payment."""
    payer_id: int = Field(..., description="Member ID of who paid")
    receiver_id: int = Field(..., description="Member ID of who received")
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    note: str | None = Field(None, max_length=1000)

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Settlement amount must be positive")
        return v

    @model_validator(mode="after")
    def payer_and_receiver_must_differ(self) -> "SettlementCreate":
        if self.payer_id == self.receiver_id:
            raise ValueError("Payer and receiver must be different members")
        return self


class SettlementResponse(BaseModel):
    """Schema for returning settlement data."""
    model_config = {"from_attributes": True}

    id: int
    group_id: int
    payer_id: int
    payer_name: str = ""
    receiver_id: int
    receiver_name: str = ""
    amount: Decimal
    note: str | None
    created_at: datetime


class SettlementSuggestion(BaseModel):
    """A suggested settlement transaction to minimize debt."""
    from_member_id: int
    from_member_name: str
    to_member_id: int
    to_member_name: str
    amount: Decimal


class BalanceResponse(BaseModel):
    """Net balance for a single member."""
    member_id: int
    member_name: str
    # Positive = owed money (others owe this member)
    # Negative = owes money (this member owes others)
    net_balance: Decimal
    total_paid: Decimal
    total_owed: Decimal


class GroupBalancesResponse(BaseModel):
    """All balances for a group, plus settlement suggestions."""
    group_id: int
    balances: list[BalanceResponse]
    settlement_suggestions: list[SettlementSuggestion]
    is_settled: bool
