"""
Authentication API routes.

POST /api/v1/auth/register  — Create new account
POST /api/v1/auth/login     — Login and set cookie
POST /api/v1/auth/logout    — Clear auth cookie
GET  /api/v1/auth/me        — Get current user
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Response, status
from bson import ObjectId

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.database import get_database
from app.models.documents import UserDocument
from app.schemas.all_schemas import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

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
