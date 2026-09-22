"""
Groups API route handlers.

Endpoints:
  GET    /api/v1/groups              — List all groups
  POST   /api/v1/groups              — Create a group
  GET    /api/v1/groups/{id}         — Get group with member details
  DELETE /api/v1/groups/{id}         — Delete a group
  GET    /api/v1/groups/{id}/members — List members
  POST   /api/v1/groups/{id}/members — Add a member
  DELETE /api/v1/groups/{id}/members/{mid} — Remove a member
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.group import Group, Member
from app.schemas.group import (
    GroupCreate,
    GroupResponse,
    GroupDetailResponse,
    MemberCreate,
    MemberResponse,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def _get_group_or_404(db: Session, group_id: int) -> Group:
    """Fetch a group by ID or raise 404."""
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Group with id={group_id} not found",
        )
    return group


@router.get("/", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db)) -> list[GroupResponse]:
    """List all groups with member counts."""
    groups = db.execute(select(Group).order_by(Group.created_at.desc())).scalars().all()
    result = []
    for group in groups:
        member_count = len(group.members)
        result.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            member_count=member_count,
        ))
    return result


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(data: GroupCreate, db: Session = Depends(get_db)) -> GroupResponse:
    """Create a new group."""
    group = Group(name=data.name, description=data.description)
    db.add(group)
    db.commit()
    db.refresh(group)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        member_count=0,
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
def get_group(group_id: int, db: Session = Depends(get_db)) -> GroupDetailResponse:
    """Get a group with full member list."""
    group = _get_group_or_404(db, group_id)
    members = [
        MemberResponse(
            id=m.id,
            group_id=m.group_id,
            name=m.name,
            created_at=m.created_at,
        )
        for m in sorted(group.members, key=lambda m: m.name)
    ]
    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        member_count=len(members),
        members=members,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db)) -> None:
    """Delete a group and all its data (cascade)."""
    group = _get_group_or_404(db, group_id)
    db.delete(group)
    db.commit()


@router.get("/{group_id}/members", response_model=list[MemberResponse])
def list_members(group_id: int, db: Session = Depends(get_db)) -> list[MemberResponse]:
    """List all members of a group."""
    _get_group_or_404(db, group_id)
    members = db.execute(
        select(Member)
        .where(Member.group_id == group_id)
        .order_by(Member.name)
    ).scalars().all()
    return [
        MemberResponse(id=m.id, group_id=m.group_id, name=m.name, created_at=m.created_at)
        for m in members
    ]


@router.post(
    "/{group_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    group_id: int, data: MemberCreate, db: Session = Depends(get_db)
) -> MemberResponse:
    """Add a member to a group. Duplicate names in the same group are rejected."""
    _get_group_or_404(db, group_id)

    # Check for duplicate name (case-insensitive)
    existing = db.execute(
        select(Member).where(
            Member.group_id == group_id,
            Member.name.ilike(data.name),
        )
    ).scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A member named '{data.name}' already exists in this group",
        )

    member = Member(group_id=group_id, name=data.name)
    db.add(member)
    db.commit()
    db.refresh(member)
    return MemberResponse(
        id=member.id,
        group_id=member.group_id,
        name=member.name,
        created_at=member.created_at,
    )


@router.delete(
    "/{group_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    group_id: int, member_id: int, db: Session = Depends(get_db)
) -> None:
    """Remove a member from a group."""
    _get_group_or_404(db, group_id)
    member = db.execute(
        select(Member).where(Member.id == member_id, Member.group_id == group_id)
    ).scalar_one_or_none()

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member with id={member_id} not found in group {group_id}",
        )

    db.delete(member)
    db.commit()
