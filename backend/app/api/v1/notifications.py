"""
Notifications API routes.

Routes:
  GET  /api/v1/notifications                — List user's notifications
  PATCH /api/v1/notifications/:id/read      — Mark one as read
  POST /api/v1/notifications/read-all       — Mark all as read
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from bson import ObjectId
from datetime import datetime, timezone

from app.core.auth import get_current_user
from app.db.database import get_database
from app.schemas.all_schemas import NotificationResponse, NotificationsListResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])
logger = logging.getLogger(__name__)


@router.get("", response_model=NotificationsListResponse)
async def list_notifications(
    limit: int = 50,
    current_user=Depends(get_current_user),
):
    """Get notifications for the current user, newest first."""
    db = get_database()
    user_id = str(current_user["_id"])

    notifications = await db.notifications.find(
        {"recipient_id": user_id},
        sort=[("created_at", -1)],
        limit=limit,
    ).to_list(limit)

    unread_count = await db.notifications.count_documents(
        {"recipient_id": user_id, "read": False}
    )

    return NotificationsListResponse(
        notifications=[
            NotificationResponse(
                id=str(n["_id"]),
                type=n["type"],
                message=n["message"],
                related_entity_id=n.get("related_entity_id"),
                related_entity_type=n.get("related_entity_type"),
                read=n["read"],
                created_at=n["created_at"],
            )
            for n in notifications
        ],
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    current_user=Depends(get_current_user),
):
    """Mark a specific notification as read."""
    db = get_database()
    user_id = str(current_user["_id"])

    if not ObjectId.is_valid(notification_id):
        raise HTTPException(status_code=400, detail="Invalid notification ID")

    nid = ObjectId(notification_id)
    notification = await db.notifications.find_one({"_id": nid})

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # Authorization: only the recipient can mark it read
    if notification["recipient_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not your notification")

    await db.notifications.update_one(
        {"_id": nid},
        {"$set": {"read": True}},
    )

    notification["read"] = True
    return NotificationResponse(
        id=str(notification["_id"]),
        type=notification["type"],
        message=notification["message"],
        related_entity_id=notification.get("related_entity_id"),
        related_entity_type=notification.get("related_entity_type"),
        read=True,
        created_at=notification["created_at"],
    )


@router.post("/read-all")
async def mark_all_read(current_user=Depends(get_current_user)):
    """Mark all notifications as read for the current user."""
    db = get_database()
    user_id = str(current_user["_id"])

    result = await db.notifications.update_many(
        {"recipient_id": user_id, "read": False},
        {"$set": {"read": True}},
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}
