"""
Notification service — creates in-app notifications for important events.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.models.documents import NotificationDocument

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncIOMotorDatabase,
    recipient_id: str,
    type: str,
    message: str,
    related_entity_id: str | None = None,
    related_entity_type: str | None = None,
) -> None:
    """Insert a notification document. Silently logs errors rather than crashing the caller."""
    try:
        doc = NotificationDocument(
            recipient_id=recipient_id,
            type=type,
            message=message,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
        )
        await db.notifications.insert_one(doc.to_dict())
    except Exception as e:
        logger.error("Failed to create notification for %s: %s", recipient_id, e)


async def notify_group_members(
    db: AsyncIOMotorDatabase,
    group: dict,
    type: str,
    message: str,
    exclude_user_id: str | None = None,
    related_entity_id: str | None = None,
    related_entity_type: str | None = None,
) -> None:
    """Send a notification to all group members (optionally excluding one user)."""
    member_ids = group.get("member_ids", [])
    for uid in member_ids:
        if exclude_user_id and uid == exclude_user_id:
            continue
        await create_notification(
            db=db,
            recipient_id=uid,
            type=type,
            message=message,
            related_entity_id=related_entity_id,
            related_entity_type=related_entity_type,
        )
