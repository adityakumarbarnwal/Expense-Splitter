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
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from jose import JWTError, jwt

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


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, response: Response):
    """
    Register a new user account.

    - Validates name, email, password
    - Checks for duplicate email
    - Hashes password with bcrypt
    - Creates user in MongoDB
    - Sets httpOnly auth cookie
    """
    db = get_database()

    # Check for duplicate email
    existing = await db.users.find_one({"email": data.email.lower()})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Create user document
    user_doc = UserDocument(
        name=data.name.strip(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    result = await db.users.insert_one(user_doc.to_dict())
    user_id = str(result.inserted_id)

    logger.info("New user registered: %s (%s)", data.email, user_id)

    # Fetch the created user
    user = await db.users.find_one({"_id": result.inserted_id})

    # Create JWT and set httpOnly cookie
    token = create_access_token(user_id=user_id, email=data.email.lower())
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="lax",
        secure=False,  # Set True in production with HTTPS
    )

    return AuthResponse(
        user=_user_to_response(user),
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

    user = await db.users.find_one({"email": data.email.lower()})
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
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
):
    """
    Request password reset OTP.

    - Normalizes email to lowercase
    - Returns generic message regardless of email existence (privacy)
    - Rate limits to 3 requests per 5 minutes
    - Generates 6-digit OTP, hashes it with bcrypt, saves to db.password_reset_otps
    - Sends OTP via email (fire-and-forget)
    """
    db = get_database()
    email = data.email.lower().strip()
    generic_message = "If an account exists for this email, a password-reset OTP has been sent."

    user = await db.users.find_one({"email": email})
    if not user:
        logger.info("Password reset requested for non-existent email (not revealing)")
        return MessageResponse(message=generic_message)

    # Rate limiting: count OTPs created in last 5 minutes for this email
    five_mins_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
    otp_count = await db.password_reset_otps.count_documents({
        "email": email,
        "created_at": {"$gte": five_mins_ago},
    })
    audit_count = await db.password_reset_audit.count_documents({
        "email": email,
        "created_at": {"$gte": five_mins_ago},
    })
    if max(otp_count, audit_count) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait before trying again.",
        )

    # Record in audit collection so rate limiting works across deletes
    await db.password_reset_audit.insert_one({
        "email": email,
        "created_at": datetime.now(timezone.utc),
    })

    # Generate 6-digit OTP: secrets.randbelow(1000000) formatted as f"{otp:06d}"
    otp_val = secrets.randbelow(1000000)
    otp_str = f"{otp_val:06d}"

    # Hash OTP using bcrypt
    otp_hash = bcrypt.hashpw(otp_str.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Delete any previous OTPs for this email
    await db.password_reset_otps.delete_many({"email": email})

    # Insert new OTP doc with expires_at = now + 10 minutes
    now = datetime.now(timezone.utc)
    otp_doc = {
        "email": email,
        "otp_hash": otp_hash,
        "expires_at": now + timedelta(minutes=10),
        "used": False,
        "attempts": 0,
        "created_at": now,
    }
    await db.password_reset_otps.insert_one(otp_doc)

    # Fire-and-forget email
    background_tasks.add_task(
        send_password_reset_otp_email,
        to_email=email,
        to_name=user.get("name", "User"),
        otp=otp_str,
    )

    logger.info("Password reset OTP generated for %s", email)
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

    otp_doc = await db.password_reset_otps.find_one({"email": email, "used": False})
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
        await db.password_reset_otps.update_one(
            {"_id": otp_doc["_id"]},
            {"$inc": {"attempts": 1}},
        )
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
    await db.password_reset_otps.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"used": True}},
    )

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

    otp_doc = await db.password_reset_otps.find_one({
        "email": email,
        "used": True,
        "reset_done": {"$ne": True},
    })
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

    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    new_hash = hash_password(data.new_password)
    now = datetime.now(timezone.utc)

    await db.users.update_one(
        {"email": email},
        {"$set": {"password_hash": new_hash, "updated_at": now}},
    )

    await db.password_reset_otps.update_one(
        {"_id": otp_doc["_id"]},
        {"$set": {"reset_done": True}},
    )

    logger.info("Password reset completed for %s", email)
    return MessageResponse(
        message="Password reset successful. Please log in with your new password."
    )

