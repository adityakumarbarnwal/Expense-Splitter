"""
Pydantic schemas for all API request/response models.
These are separate from the MongoDB document models.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ──────────────────────────────────────────────
# Auth Schemas
# ──────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    created_at: datetime


class AuthResponse(BaseModel):
    user: UserResponse
    message: str = "Login successful"


# ──────────────────────────────────────────────
# Profile Schemas
# ──────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be blank")
        return v.strip()


# ──────────────────────────────────────────────
# Group Schemas
# ──────────────────────────────────────────────

class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Group name cannot be blank")
        return v.strip()


class UpdateGroupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Group name cannot be blank")
        return v.strip()


class MemberInfo(BaseModel):
    id: str
    name: str
    email: str


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_by: str
    members: list[MemberInfo] = []
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class GroupListItem(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    member_count: int
    created_at: datetime
    user_net_balance: Optional[float] = None  # Current user's net position in this group


# ──────────────────────────────────────────────
# Member Schemas
# ──────────────────────────────────────────────

class AddMemberRequest(BaseModel):
    email: EmailStr


# ──────────────────────────────────────────────
# Expense Schemas
# ──────────────────────────────────────────────

class ExpenseParticipantRequest(BaseModel):
    user_id: str


class CreateExpenseRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., gt=0, le=10_000_000)
    payer_id: str  # User _id
    participant_ids: list[str] = Field(..., min_length=1)
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("participant_ids")
    @classmethod
    def no_duplicate_participants(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("Duplicate participant IDs are not allowed")
        return v

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Description cannot be blank")
        return v.strip()


class UpdateExpenseRequest(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    amount: Optional[float] = Field(None, gt=0, le=10_000_000)
    payer_id: Optional[str] = None
    participant_ids: Optional[list[str]] = None
    note: Optional[str] = Field(None, max_length=500)


class ExpenseParticipantResponse(BaseModel):
    user_id: str
    name: str
    share: float


class ExpenseResponse(BaseModel):
    id: str
    group_id: str
    description: str
    amount: float
    payer_id: str
    payer_name: str
    participants: list[ExpenseParticipantResponse]
    note: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────────────────────
# Balance Schemas
# ──────────────────────────────────────────────

class MemberBalanceResponse(BaseModel):
    user_id: str
    member_name: str
    total_paid: float
    total_owed: float
    settlements_paid: float
    settlements_received: float
    net_balance: float


class SettlementSuggestion(BaseModel):
    from_user_id: str
    from_member_name: str
    to_user_id: str
    to_member_name: str
    amount: float


class GroupBalancesResponse(BaseModel):
    group_id: str
    balances: list[MemberBalanceResponse]
    settlement_suggestions: list[SettlementSuggestion]
    is_settled: bool


# ──────────────────────────────────────────────
# Settlement Schemas
# ──────────────────────────────────────────────

class CreateSettlementRequest(BaseModel):
    payer_id: str   # User _id of who paid
    receiver_id: str  # User _id of who received
    amount: float = Field(..., gt=0, le=10_000_000)
    note: Optional[str] = Field(None, max_length=500)

    @field_validator("receiver_id")
    @classmethod
    def different_payer_receiver(cls, v: str, info) -> str:
        if "payer_id" in info.data and v == info.data["payer_id"]:
            raise ValueError("Payer and receiver must be different")
        return v


class SettlementResponse(BaseModel):
    id: str
    group_id: str
    payer_id: str
    payer_name: str
    receiver_id: str
    receiver_name: str
    amount: float
    note: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None



# ──────────────────────────────────────────────
# Notification Schemas
# ──────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: str
    type: str
    message: str
    related_entity_id: Optional[str] = None
    related_entity_type: Optional[str] = None
    read: bool
    created_at: datetime


class NotificationsListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int


# ──────────────────────────────────────────────
# AI Schemas
# ──────────────────────────────────────────────

class AIParseRequest(BaseModel):
    group_id: str
    text: str = Field(..., min_length=1, max_length=2000)
    current_user_name: Optional[str] = None


class AIParseResult(BaseModel):
    description: Optional[str] = None
    amount: Optional[float] = None
    payer_name: Optional[str] = None
    participant_names: list[str] = Field(default_factory=list)
    confidence: str = "low"
    notes: Optional[str] = None


class AIParseResponse(BaseModel):
    success: bool
    result: Optional[AIParseResult] = None
    warnings: list[str] = Field(default_factory=list)
    error: Optional[str] = None
    original_text: str = ""


# ──────────────────────────────────────────────
# Dashboard Schema
# ──────────────────────────────────────────────

class DashboardResponse(BaseModel):
    total_groups: int
    you_owe: float
    you_are_owed: float
    net_balance: float
    recent_expenses: list[ExpenseResponse]
    groups: list[GroupListItem]


# ──────────────────────────────────────────────
# Password Reset / OTP Schemas
# ──────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    reset_token: str
    message: str


class ResetPasswordRequest(BaseModel):
    reset_token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class MessageResponse(BaseModel):
    message: str


# ──────────────────────────────────────────────
# Settlement Update Schema
# ──────────────────────────────────────────────

class UpdateSettlementRequest(BaseModel):
    payer_id: Optional[str] = None
    receiver_id: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0, le=10_000_000)
    note: Optional[str] = Field(None, max_length=500)

