"""
MongoDB document models using Pydantic.

These are NOT SQLAlchemy models — they are Pydantic models that represent
MongoDB documents. _id fields use PyObjectId for proper serialization.
"""

from datetime import datetime, timezone
from typing import Annotated, Any
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator, model_validator


class PyObjectId(str):
    """Custom type for MongoDB ObjectId that serializes as a string."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str) and ObjectId.is_valid(v):
            return v
        if v is None:
            return v
        raise ValueError(f"Invalid ObjectId: {v}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.no_info_plain_validator_function(
            cls._validate,
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, v: Any) -> str:
        if isinstance(v, ObjectId):
            return str(v)
        if isinstance(v, str):
            if ObjectId.is_valid(v):
                return v
            if v == "":
                return v
        if v is None:
            return v
        raise ValueError(f"Invalid ObjectId: {v!r}")


def utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


# ──────────────────────────────────────────────
# User Model
# ──────────────────────────────────────────────

class UserDocument(BaseModel):
    """MongoDB user document."""

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    name: str
    email: str
    password_hash: str
    avatar_url: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict:
        """Convert to MongoDB-compatible dict (without id, using _id)."""
        d = self.model_dump(exclude={"id"}, by_alias=False)
        return d


# ──────────────────────────────────────────────
# Group Model
# ──────────────────────────────────────────────

class GroupDocument(BaseModel):
    """MongoDB group document."""

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    name: str
    description: str | None = None
    created_by: str  # User _id as string
    member_ids: list[str] = Field(default_factory=list)  # List of User _ids
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict:
        d = self.model_dump(exclude={"id"}, by_alias=False)
        return d


# ──────────────────────────────────────────────
# Expense Model
# ──────────────────────────────────────────────

class ExpenseParticipantDoc(BaseModel):
    """Embedded participant with share amount."""
    user_id: str  # User _id
    name: str     # Denormalized name for display
    share: float  # Their calculated share


class ExpenseDocument(BaseModel):
    """MongoDB expense document."""

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    group_id: str
    description: str
    amount: float
    payer_id: str     # User _id
    payer_name: str   # Denormalized
    participants: list[ExpenseParticipantDoc] = Field(default_factory=list)
    note: str | None = None
    created_by: str   # User _id of whoever recorded it
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict:
        d = self.model_dump(exclude={"id"}, by_alias=False)
        return d


# ──────────────────────────────────────────────
# Settlement Model
# ──────────────────────────────────────────────

class SettlementDocument(BaseModel):
    """MongoDB settlement document."""

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    group_id: str
    payer_id: str        # User who paid
    payer_name: str      # Denormalized
    receiver_id: str     # User who received
    receiver_name: str   # Denormalized
    amount: float
    note: str | None = None
    created_by: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        d = self.model_dump(exclude={"id"}, by_alias=False)
        return d


# ──────────────────────────────────────────────
# Notification Model
# ──────────────────────────────────────────────

class NotificationDocument(BaseModel):
    """MongoDB notification document."""

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}

    id: PyObjectId | None = Field(default=None, alias="_id")
    recipient_id: str       # User _id
    type: str               # e.g. "expense_added", "group_created", "member_added"
    message: str
    related_entity_id: str | None = None   # e.g. group_id or expense_id
    related_entity_type: str | None = None  # "group", "expense", "settlement"
    read: bool = False
    created_at: datetime = Field(default_factory=utcnow)

    def to_dict(self) -> dict:
        d = self.model_dump(exclude={"id"}, by_alias=False)
        return d
