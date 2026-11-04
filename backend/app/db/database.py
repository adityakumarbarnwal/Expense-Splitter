"""
MongoDB database connection using Motor (async MongoDB driver).

Provides:
- AsyncIOMotorClient singleton
- Database instance
- Startup/shutdown lifecycle management
- Index creation

Connection reliability notes:
- Atlas M0 free tier drops idle connections after ~60 seconds.
  maxIdleTimeMS=30000 ensures the driver retires connections before Atlas
  closes them, preventing "NetworkTimeout on first use after idle" errors.
- serverSelectionTimeoutMS=10s surfaces Atlas unreachability quickly.
- socketTimeoutMS=20s gives active operations enough time to complete on
  the Atlas free tier (which is slower than paid tiers).
- The client is initialized ONCE at startup; get_database() returns the
  singleton. Never call AsyncIOMotorClient() per-request.
"""

import logging
import re
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level client and db — initialized in lifespan
_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _mask_uri(uri: str) -> str:
    """Mask credentials in a MongoDB URI for safe logging."""
    masked = re.sub(r"(mongodb(?:\+srv)?://)([^:]+):([^@]+)@", r"\1***:***@", uri)
    return masked


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

    masked_uri = _mask_uri(settings.mongodb_uri)
    logger.info("Connecting to MongoDB — URI: %s  DB: %s", masked_uri, settings.mongodb_db_name)

    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        # How long to wait for a suitable server in the topology.
        # 10s is enough for Atlas; shorter surfaces connectivity problems fast.
        serverSelectionTimeoutMS=10_000,
        # Individual socket connect timeout.
        connectTimeoutMS=10_000,
        # Individual socket operation timeout.
        # Atlas M0 is slower than paid tiers — 20s prevents premature timeouts
        # on legitimate slow operations while still surfacing real hangs.
        socketTimeoutMS=20_000,
        # KEY FIX for "NetworkTimeout on first use after idle":
        # Atlas M0 closes idle connections after ~60s. Setting maxIdleTimeMS
        # to 30s ensures the driver retires connections before Atlas drops them,
        # so the next request always gets a fresh connection rather than a stale one.
        maxIdleTimeMS=30_000,
        # Small pool — adequate for a dev/academic app.
        maxPoolSize=10,
        # Minimum connections to keep open — avoids cold-start latency.
        minPoolSize=1,
        # Retry reads automatically on a stale connection (Motor/pymongo default).
        retryReads=True,
        # Retry writes automatically — safe for insert/update with unique indexes.
        retryWrites=True,
    )
    _db = _client[settings.mongodb_db_name]

    # Verify connection with a ping
    try:
        await _db.command("ping")
        logger.info("MongoDB connected successfully to database '%s'", settings.mongodb_db_name)
    except ServerSelectionTimeoutError as e:
        error_str = str(e)
        if "TLSV1_ALERT_INTERNAL_ERROR" in error_str or "SSL handshake failed" in error_str:
            logger.error(
                "MongoDB TLS/SSL handshake FAILED — most likely causes:\n"
                "  1. Your IP is NOT in the MongoDB Atlas Network Access allowlist.\n"
                "     Go to: Atlas → Network Access → Add IP Address.\n"
                "     For development: allow 0.0.0.0/0 (all IPs).\n"
                "  2. The Atlas cluster is paused or deleted.\n"
                "  3. A firewall/antivirus is intercepting TLS on port 27017.\n"
                "Connection string (masked): %s",
                masked_uri,
            )
        elif "Authentication failed" in error_str:
            logger.error(
                "MongoDB authentication FAILED — check MONGODB_URI username and password.\n"
                "Connection string (masked): %s",
                masked_uri,
            )
        elif "getaddrinfo failed" in error_str or "nodename nor servname" in error_str:
            logger.error(
                "MongoDB DNS resolution FAILED — cannot resolve the hostname.\n"
                "Check network connectivity and your MONGODB_URI hostname.\n"
                "Connection string (masked): %s",
                masked_uri,
            )
        else:
            logger.error(
                "MongoDB connection FAILED — ServerSelectionTimeoutError.\n"
                "Connection string (masked): %s\n"
                "Error: %s",
                masked_uri,
                error_str[:300],
            )
        _client.close()
        _client = None
        _db = None
        raise

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
