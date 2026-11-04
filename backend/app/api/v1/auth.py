"""
Authentication API routes.

POST /api/v1/auth/register        — Create new account
POST /api/v1/auth/login           — Login and set cookie
POST /api/v1/auth/logout          — Clear auth cookie
GET  /api/v1/auth/me              — Get current user
POST /api/v1/auth/forgot-password — Request password reset OTP
POST /api/v1/auth/verify-otp      — Verify OTP and receive reset token
POST /api/v1/auth/reset-password  — Reset password using reset token
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError, jwt
from pymongo.errors import PyMongoError

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.db.database import get_database
from app.models.documents import UserDocument
from app.schemas.all_schemas import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.services.email_service import send_password_reset_otp_email

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)
settings = get_settings()

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days in seconds


def _user_to_response(user: dict) -> UserResponse:
    return UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        email=user["email"],
        avatar_url=user.get("avatar_url"),
        created_at=user["created_at"],
    )


def _build_user_response_from_doc(user_doc: UserDocument, inserted_id) -> UserResponse:
    """
    Build a UserResponse directly from the document we inserted, without
    fetching it back from the database.

    This avoids an extra DB round-trip that can hit a stale connection
    (the confirmed cause of NetworkTimeout at auth.py:96).
    """
    doc_dict = user_doc.to_dict()
    doc_dict["_id"] = inserted_id
    return UserResponse(
        id=str(inserted_id),
        name=doc_dict["name"],
        email=doc_dict["email"],
        avatar_url=doc_dict.get("avatar_url"),
        created_at=doc_dict["created_at"],
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, response: Response):
    """
    Register a new user account.

    - Validates name, email, password
    - Checks for duplicate email (409 on conflict)
    - Hashes password with bcrypt
    - Creates user in MongoDB
    - Builds response from inserted data — no second DB read
    - Sets httpOnly auth cookie
    - Redirects intent: frontend should navigate to /login after success
    """
    db = get_database()

    # Check for duplicate email — normalize to lowercase consistently
    email_normalized = data.email.lower().strip()
    try:
        existing = await db.users.find_one({"email": email_normalized})
    except PyMongoError as e:
        logger.error("DB error during duplicate-email check for %s: %s", email_normalized, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again in a moment.",
        )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Create user document
    user_doc = UserDocument(
        name=data.name.strip(),
        email=email_normalized,
        password_hash=hash_password(data.password),
    )

    try:
        result = await db.users.insert_one(user_doc.to_dict())
    except PyMongoError as e:
        logger.error("DB error during user insertion for %s: %s", email_normalized, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not create account due to a database error. Please try again.",
        )

    user_id = str(result.inserted_id)
    logger.info("New user registered: %s (%s)", email_normalized, user_id)

    # Build response from the data we already have — no second DB read.
    # Previously line 96 did `db.users.find_one({"_id": result.inserted_id})`
    # which would hit a potentially stale connection immediately after insert,
    # causing the observed NetworkTimeout.
    user_response = _build_user_response_from_doc(user_doc, result.inserted_id)

    # Create JWT and set httpOnly cookie
    token = create_access_token(user_id=user_id, email=email_normalized)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
    )

    return AuthResponse(
        user=user_response,
        message="Account created successfully",
    )


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, response: Response):
    """
    Login with email and password.

    - Finds user by email
    - Verifies password with bcrypt
    - Sets httpOnly auth cookie
    """
    db = get_database()

    try:
        user = await db.users.find_one({"email": data.email.lower().strip()})
    except PyMongoError as e:
        logger.error("DB error during login for %s: %s", data.email, e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    user_id = str(user["_id"])
    token = create_access_token(user_id=user_id, email=user["email"])
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        secure=False,
    )

    logger.info("User logged in: %s", user["email"])
    return AuthResponse(user=_user_to_response(user), message="Login successful")


@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie."""
    response.delete_cookie(key=COOKIE_NAME, samesite="lax")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get the currently authenticated user's profile."""
    return _user_to_response(current_user)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest):
    """
    Request password reset OTP.

    - Normalizes email to lowercase
    - Returns SAME generic message whether email exists or not (privacy)
    - Rate limits: max 3 OTP requests per 5 minutes per email
    - Generates cryptographically secure 6-digit OTP
    - Stores ONLY the bcrypt hash — never the plaintext OTP
    - Awaits email delivery; deletes OTP from DB if delivery fails
    - If MAIL_ENABLED=False, returns generic message without storing OTP
    """
    db = get_database()
    email = data.email.lower().strip()
    generic_message = "If an account exists for this email, a password-reset OTP has been sent."

    # Privacy: same response whether email is registered or not
    try:
        user = await db.users.find_one({"email": email})
    except PyMongoError as e:
        logger.error("DB error during forgot-password lookup: %s", e)
        # Return generic message — don't reveal DB state to caller
        return MessageResponse(message=generic_message)

    if not user:
        logger.info("Password reset requested for non-registered email (not revealing to caller)")
        return MessageResponse(message=generic_message)

    # If email is disabled, log and return generic message — do NOT store an OTP
    if not settings.mail_enabled:
        logger.warning(
            "MAIL_ENABLED=False — OTP not generated for %s. "
            "Set MAIL_ENABLED=True and configure SMTP to enable password reset emails.",
            email,
        )
        return MessageResponse(message=generic_message)

    # Rate limiting: count OTPs created in last 5 minutes for this email
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    try:
        otp_count = await db.password_reset_otps.count_documents({
            "email": email,
            "created_at": {"$gte": five_mins_ago},
        })
        audit_count = await db.password_reset_audit.count_documents({
            "email": email,
            "created_at": {"$gte": five_mins_ago},
        })
    except PyMongoError as e:
        logger.error("DB error during OTP rate-limit check: %s", e)
        return MessageResponse(message=generic_message)

    if max(otp_count, audit_count) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait before trying again.",
        )

    # Record in audit collection (rate-limiting survives OTP deletion)
    try:
        await db.password_reset_audit.insert_one({
            "email": email,
            "created_at": datetime.now(timezone.utc),
        })
    except PyMongoError as e:
        logger.error("DB error writing OTP audit entry: %s", e)
        return MessageResponse(message=generic_message)

    # Generate cryptographically secure 6-digit OTP
    otp_val = secrets.randbelow(1000000)
    otp_str = f"{otp_val:06d}"

    # Store ONLY the bcrypt hash — never log or return the plaintext OTP
    otp_hash = bcrypt.hashpw(otp_str.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Invalidate any previous unused OTPs for this email
    try:
        await db.password_reset_otps.delete_many({"email": email})
    except PyMongoError:
        pass  # Non-critical — the new OTP will supersede the old one

    # Persist new OTP (expires in 10 minutes)
    now = datetime.now(timezone.utc)
    otp_doc = {
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": now + timedelta(minutes=10),
        "used": False,
        "attempts": 0,
        "created_at": now,
    }
    try:
        inserted = await db.password_reset_otps.insert_one(otp_doc)
        otp_id = inserted.inserted_id
    except PyMongoError as e:
        logger.error("DB error storing OTP: %s", e)
        return MessageResponse(message=generic_message)

    # Send OTP email — AWAITED so failures are caught here, not silently dropped
    email_sent = await send_password_reset_otp_email(
        to_email=email,
        to_name=user.get("name", "User"),
        otp=otp_str,
    )

    if not email_sent:
        # Clean up the OTP so it cannot be used without the email being delivered
        try:
            await db.password_reset_otps.delete_one({"_id": otp_id})
        except PyMongoError:
            pass
        logger.error(
            "OTP email delivery failed for %s — OTP invalidated to prevent phantom reset tokens",
            email,
        )
        return MessageResponse(message=generic_message)

    logger.info("Password reset OTP generated and email dispatched for %s", email)
    return MessageResponse(message=generic_message)


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(data: VerifyOTPRequest):
    """
    Verify OTP sent to user's email.

    - Verifies OTP against bcrypt hash
    - Checks attempts < 5 and expiry
    - Issues a 15-minute JWT reset token with purpose=password_reset
    - Marks OTP as used
    """
    db = get_database()
    email = data.email.lower().strip()

    try:
        otp_doc = await db.password_reset_otps.find_one({"email": email, "used": False})
    except PyMongoError as e:
        logger.error("DB error during OTP verification: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )

    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP found. Please request a new one.",
        )

    if otp_doc.get("attempts", 0) >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many incorrect attempts. Please request a new OTP.",
        )

    now = datetime.now(timezone.utc)
    expires_at = otp_doc.get("expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if now > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP has expired. Please request a new one.",
            )

    is_valid = False
    try:
        is_valid = bcrypt.checkpw(
            data.otp.encode("utf-8"),
            otp_doc["otp_hash"].encode("utf-8"),
        )
    except Exception:
        is_valid = False

    if not is_valid:
        try:
            await db.password_reset_otps.update_one(
                {"_id": otp_doc["_id"]},
                {"$inc": {"attempts": 1}},
            )
        except PyMongoError:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect OTP.",
        )

    # Generate short-lived reset token (JWT, 15 minutes, with purpose=password_reset claim)
    payload = {
        "sub": email,
        "purpose": "password_reset",
        "exp": now + timedelta(minutes=15),
        "iat": now,
    }
    reset_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Mark OTP as used
    try:
        await db.password_reset_otps.update_one(
            {"_id": otp_doc["_id"]},
            {"$set": {"used": True}},
        )
    except PyMongoError as e:
        logger.error("DB error marking OTP as used: %s", e)

    logger.info("OTP verified for %s", email)
    return VerifyOTPResponse(
        reset_token=reset_token,
        message="OTP verified. You may now reset your password.",
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest):
    """
    Reset password using reset token.

    - Validates JWT reset token and purpose claim
    - Verifies used=True OTP exists and reset_done is not True
    - Validates new password length >= 8
    - Hashes password with hash_password from app.core.auth
    - Updates user in MongoDB
    - Marks OTP as reset_done=True
    """
    db = get_database()

    try:
        payload = jwt.decode(
            data.reset_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset token.",
        )

    if payload.get("purpose") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset token.",
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid reset token.",
        )
    email = email.lower().strip()

    try:
        otp_doc = await db.password_reset_otps.find_one({
            "email": email,
            "used": True,
            "reset_done": {"$ne": True},
        })
    except PyMongoError as e:
        logger.error("DB error during reset-password OTP lookup: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )

    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used or is invalid.",
        )

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )

    try:
        user = await db.users.find_one({"email": email})
    except PyMongoError as e:
        logger.error("DB error fetching user during password reset: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    new_hash = hash_password(data.new_password)
    now = datetime.now(timezone.utc)

    try:
        await db.users.update_one(
            {"email": email},
            {"$set": {"password_hash": new_hash, "updated_at": now}},
        )
        await db.password_reset_otps.update_one(
            {"_id": otp_doc["_id"]},
            {"$set": {"reset_done": True}},
        )
    except PyMongoError as e:
        logger.error("DB error during password update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database temporarily unavailable. Please try again.",
        )

    logger.info("Password reset completed for %s", email)
    return MessageResponse(
        message="Password reset successful. Please log in with your new password."
    )
