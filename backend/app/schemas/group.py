"""
Pydantic schemas for Group and Member API request/response validation.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ===========================
# Group Schemas
# ===========================

class GroupCreate(BaseModel):
    """Schema for creating a new group."""
    name: str = Field(..., min_length=1, max_length=255, description="Group name")
    description: str | None = Field(None, max_length=1000, description="Optional description")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Group name cannot be blank")
        return v.strip()


class GroupUpdate(BaseModel):
    """Schema for updating a group."""
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class GroupResponse(BaseModel):
    """Schema for returning group data."""
    model_config = {"from_attributes": True}

    id: int
    name: str
    description: str | None
    created_at: datetime
    member_count: int = 0


class GroupDetailResponse(GroupResponse):
    """Group response with full member list."""
    members: list["MemberResponse"] = []


# ===========================
# Member Schemas
# ===========================

class MemberCreate(BaseModel):
    """Schema for adding a member to a group."""
    name: str = Field(..., min_length=1, max_length=100, description="Member's name")

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Member name cannot be blank")
        return v.strip()


class MemberResponse(BaseModel):
    """Schema for returning member data."""
    model_config = {"from_attributes": True}

    id: int
    group_id: int
    name: str
    created_at: datetime


# Resolve forward reference
GroupDetailResponse.model_rebuild()
