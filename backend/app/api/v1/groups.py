"""
Groups API routes — MongoDB backend.

All routes require authentication.
Authorization: user must be a member of the group to access it.

Routes:
  GET    /api/v1/groups                    — List user's groups
  POST   /api/v1/groups                    — Create group
  GET    /api/v1/groups/:id                — Get group detail
  PATCH  /api/v1/groups/:id               — Rename group
  POST   /api/v1/groups/:id/members        — Add member by email
  DELETE /api/v1/groups/:id/members/:uid   — Remove member
  GET    /api/v1/groups/:id/members        — List members
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from bson import ObjectId

from app.core.auth import get_current_user
from app.db.database import get_database
from app.models.documents import GroupDocument
from app.schemas.all_schemas import (
    AddMemberRequest,
    CreateGroupRequest,
    GroupListItem,
    GroupResponse,
    MemberInfo,
    UpdateGroupRequest,
)
from app.services.notification_service import create_notification, notify_group_members
from app.services.email_service import send_group_invitation_email

router = APIRouter(prefix="/groups", tags=["groups"])
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _require_valid_object_id(id_str: str, name: str = "ID") -> ObjectId:
    if not ObjectId.is_valid(id_str):
        raise HTTPException(status_code=400, detail=f"Invalid {name}: {id_str!r}")
    return ObjectId(id_str)


async def _get_group_or_404(db, group_id_str: str) -> dict:
    oid = _require_valid_object_id(group_id_str, "group ID")
    group = await db.groups.find_one({"_id": oid})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


async def _require_member(group: dict, user_id: str) -> None:
    """Raise 403 if user is not a member of the group."""
    if user_id not in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this group.",
        )


async def _get_members_info(db, member_ids: list[str]) -> list[MemberInfo]:
    """Fetch user details for a list of member IDs."""
    members = []
    for uid in member_ids:
        if not ObjectId.is_valid(uid):
            continue
        user = await db.users.find_one(
            {"_id": ObjectId(uid)},
            {"name": 1, "email": 1},
        )
        if user:
            members.append(MemberInfo(
                id=uid,
                name=user["name"],
                email=user["email"],
            ))
    return members


async def _build_group_response(db, group: dict) -> GroupResponse:
    members_info = await _get_members_info(db, group.get("member_ids", []))
    return GroupResponse(
        id=str(group["_id"]),
        name=group["name"],
        description=group.get("description"),
        created_by=group["created_by"],
        members=members_info,
        member_count=len(members_info),
        created_at=group["created_at"],
        updated_at=group["updated_at"],
    )


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────

@router.get("", response_model=list[GroupListItem])
async def list_groups(current_user=Depends(get_current_user)):
    """List all groups the authenticated user belongs to."""
    db = get_database()
    user_id = str(current_user["_id"])

    groups = await db.groups.find(
        {"member_ids": user_id},
        sort=[("created_at", -1)],
    ).to_list(100)

    result = []
    for g in groups:
        result.append(GroupListItem(
            id=str(g["_id"]),
            name=g["name"],
            description=g.get("description"),
            member_count=len(g.get("member_ids", [])),
            created_at=g["created_at"],
        ))
    return result


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: CreateGroupRequest,
    current_user=Depends(get_current_user),
):
    """Create a new group. The creator is automatically added as the first member."""
    db = get_database()
    user_id = str(current_user["_id"])

    group_doc = GroupDocument(
        name=data.name,
        description=data.description,
        created_by=user_id,
        member_ids=[user_id],
    )
    result = await db.groups.insert_one(group_doc.to_dict())
    group = await db.groups.find_one({"_id": result.inserted_id})
    group_id = str(result.inserted_id)

    # Create notification for creator
    await create_notification(
        db=db,
        recipient_id=user_id,
        type="group_created",
        message=f"You created the group \"{data.name}\".",
        related_entity_id=group_id,
        related_entity_type="group",
    )

    logger.info("Group created: %s by user %s", data.name, user_id)
    return await _build_group_response(db, group)


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user=Depends(get_current_user),
):
    """Get group details. User must be a member."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)
    return await _build_group_response(db, group)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    data: UpdateGroupRequest,
    current_user=Depends(get_current_user),
):
    """
    Rename a group.

    Authorization rule: any current group member can rename the group.
    This is documented in ADR-005.
    """
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    old_name = group["name"]
    await db.groups.update_one(
        {"_id": group["_id"]},
        {"$set": {"name": data.name, "updated_at": datetime.now(timezone.utc)}},
    )

    updated_group = await db.groups.find_one({"_id": group["_id"]})

    # Notify all members
    await notify_group_members(
        db=db,
        group=updated_group,
        type="group_renamed",
        message=f"\"{old_name}\" was renamed to \"{data.name}\".",
        related_entity_id=group_id,
        related_entity_type="group",
    )

    logger.info("Group %s renamed from '%s' to '%s'", group_id, old_name, data.name)
    return await _build_group_response(db, updated_group)


@router.get("/{group_id}/members", response_model=list[MemberInfo])
async def list_members(
    group_id: str,
    current_user=Depends(get_current_user),
):
    """List all members of a group."""
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)
    return await _get_members_info(db, group.get("member_ids", []))


@router.post("/{group_id}/members", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    group_id: str,
    data: AddMemberRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
):
    """
    Add a member to a group by their registered email address.

    Rules:
    - Requester must be a group member
    - Target user must have a registered account with that email
    - Duplicate membership is prevented
    - Email notification is sent in background (failure does not affect membership)
    """
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    # Find registered user by email
    target_user = await db.users.find_one({"email": data.email.lower()})
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No registered account found for email '{data.email}'. "
                   f"The person must create an account first.",
        )

    target_id = str(target_user["_id"])

    # Check for duplicate membership
    if target_id in group.get("member_ids", []):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{target_user['name']} is already a member of this group.",
        )

    # Add member
    await db.groups.update_one(
        {"_id": group["_id"]},
        {
            "$addToSet": {"member_ids": target_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )

    updated_group = await db.groups.find_one({"_id": group["_id"]})

    # In-app notifications
    # Notify the new member
    await create_notification(
        db=db,
        recipient_id=target_id,
        type="added_to_group",
        message=f"{current_user['name']} added you to the group \"{group['name']}\".",
        related_entity_id=group_id,
        related_entity_type="group",
    )
    # Notify existing members
    await notify_group_members(
        db=db,
        group=updated_group,
        type="member_added",
        message=f"{target_user['name']} was added to \"{group['name']}\".",
        exclude_user_id=target_id,
        related_entity_id=group_id,
        related_entity_type="group",
    )

    # Send email in background (failure does not affect response)
    background_tasks.add_task(
        send_group_invitation_email,
        to_email=target_user["email"],
        to_name=target_user["name"],
        group_name=group["name"],
        inviter_name=current_user["name"],
    )

    logger.info("User %s added to group %s by %s", target_id, group_id, user_id)
    return await _build_group_response(db, updated_group)


@router.delete("/{group_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    group_id: str,
    member_user_id: str,
    current_user=Depends(get_current_user),
):
    """
    Remove a member from a group.

    Rules:
    - Requester must be a group member
    - Cannot remove the group creator (for MVP)
    """
    db = get_database()
    user_id = str(current_user["_id"])
    group = await _get_group_or_404(db, group_id)
    await _require_member(group, user_id)

    if member_user_id == group["created_by"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the group creator.",
        )

    if member_user_id not in group.get("member_ids", []):
        raise HTTPException(status_code=404, detail="User is not a member of this group.")

    await db.groups.update_one(
        {"_id": group["_id"]},
        {
            "$pull": {"member_ids": member_user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
