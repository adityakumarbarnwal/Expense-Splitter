import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from bson import ObjectId
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pymongo.errors import PyMongoError

from app.core.config import get_settings
from app.db.database import get_database, retry_db_read

logger = logging.getLogger(__name__)
settings = get_settings()

security = HTTPBearer(auto_error=False)


# ──────────────────────────────────────────────
# Password utilities
# ──────────────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


# ──────────────────────────────────────────────
# JWT token utilities
# ──────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expires_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    """
    Decode and verify a JWT token.

    Raises:
        HTTPException 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError as e:
        logger.debug("JWT decode error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ──────────────────────────────────────────────
# FastAPI dependency — get current authenticated user
# ──────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Dependency that extracts and validates the current authenticated user.

    Checks (in order):
    1. Authorization: Bearer <token> header
    2. access_token cookie (httpOnly cookie set at login)

    Returns the user document dict from MongoDB.

    Error responses:
    - 401 Unauthorized: no token, invalid JWT, expired JWT, or user not found in DB
    - 503 Service Unavailable: JWT is valid but MongoDB timed out or is unreachable
      (this prevents legitimate sessions from being invalidated during DB hiccups)
    """
    token = None

    # 1. Try Bearer header
    if credentials and credentials.credentials:
        token = credentials.credentials

    # 2. Try httpOnly cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate JWT (raises 401 on invalid/expired token)
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    # Fetch user from MongoDB with retry on stale Atlas connections.
    # IMPORTANT: PyMongoError (timeout, network) must NOT become 401.
    # A timeout means the database is temporarily unreachable, not that the
    # token is invalid. Returning 401 on a DB timeout would log the user out
    # on the frontend, losing a valid session unnecessarily.
    db = get_database()
    try:
        user = await retry_db_read(
            lambda: db.users.find_one({"_id": ObjectId(user_id)})
        )
    except PyMongoError as e:
        logger.error(
            "Database error while retrieving user %s in get_current_user: %s",
            user_id, e,
        )
        # 503 — the token is valid but the DB is temporarily unavailable.
        # The frontend should retry, not log the user out.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again in a moment.",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
        )

    return user


async def get_current_user_id(current_user=Depends(get_current_user)) -> str:
    """Return just the current user's ID as a string."""
    return str(current_user["_id"])
