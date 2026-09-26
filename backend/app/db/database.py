"""
MongoDB database connection using Motor (async MongoDB driver).

Provides:
- AsyncIOMotorClient singleton
- Database instance
- Startup/shutdown lifecycle management
- Index creation
"""

import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client and db — initialized in lifespan
_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Database client not initialized. Call connect_db() first.")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return _db


async def connect_db() -> None:
    """Connect to MongoDB and create indexes."""
    global _client, _db
    logger.info("Connecting to MongoDB at %s / %s", settings.mongodb_uri, settings.mongodb_db_name)
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_db_name]

    # Verify connection — Motor's proper async ping
    await _client.server_info()
    logger.info("MongoDB connected successfully")

    # Create indexes
    await _create_indexes(_db)
    logger.info("MongoDB indexes ensured")


async def disconnect_db() -> None:
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB disconnected")


async def _create_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all required indexes for the application collections."""

    # Users: unique email index (critical for auth + member lookup by email)
    await db.users.create_indexes([
        IndexModel([("email", ASCENDING)], unique=True, name="idx_users_email"),
        IndexModel([("created_at", DESCENDING)], name="idx_users_created_at"),
    ])

    # Groups: index by member_ids and creator
    await db.groups.create_indexes([
        IndexModel([("member_ids", ASCENDING)], name="idx_groups_member_ids"),
        IndexModel([("created_by", ASCENDING)], name="idx_groups_created_by"),
        IndexModel([("created_at", DESCENDING)], name="idx_groups_created_at"),
    ])

    # Expenses: index by group_id and created_at for efficient listing
    await db.expenses.create_indexes([
        IndexModel([("group_id", ASCENDING), ("created_at", DESCENDING)], name="idx_expenses_group_date"),
        IndexModel([("payer_id", ASCENDING)], name="idx_expenses_payer"),
        IndexModel([("created_by", ASCENDING)], name="idx_expenses_created_by"),
    ])

    # Settlements: index by group_id
    await db.settlements.create_indexes([
        IndexModel([("group_id", ASCENDING), ("created_at", DESCENDING)], name="idx_settlements_group_date"),
    ])

    # Notifications: index by recipient + read status for efficient notification center
    await db.notifications.create_indexes([
        IndexModel([("recipient_id", ASCENDING), ("read", ASCENDING), ("created_at", DESCENDING)], name="idx_notifications_recipient"),
        IndexModel([("created_at", DESCENDING)], name="idx_notifications_created_at"),
    ])
