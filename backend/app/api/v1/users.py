"""
User profile routes.

GET   /api/v1/users/me        — Get own profile
PATCH /api/v1/users/me        — Update name only (email is immutable)
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId

from app.core.auth import get_current_user
from app.db.database import get_database
from app.schemas.all_schemas import UpdateProfileRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user=Depends(get_current_user)):
    """Get current user's profile."""
    return UserResponse(
        id=str(current_user["_id"]),
        name=current_user["name"],
        email=current_user["email"],
        avatar_url=current_user.get("avatar_url"),
        created_at=current_user["created_at"],
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UpdateProfileRequest,
    current_user=Depends(get_current_user),
):
    """
    Update profile.

    ONLY name is editable.
    Email is permanently immutable — backend enforces this regardless of frontend.
    """
    db = get_database()
    user_id = current_user["_id"]

    update = {
        "$set": {
            "name": data.name,
            "updated_at": datetime.now(timezone.utc),
        }
    }
    await db.users.update_one({"_id": user_id}, update)

    updated_user = await db.users.find_one({"_id": user_id})
    return UserResponse(
        id=str(updated_user["_id"]),
        name=updated_user["name"],
        email=updated_user["email"],
        avatar_url=updated_user.get("avatar_url"),
        created_at=updated_user["created_at"],
    )
