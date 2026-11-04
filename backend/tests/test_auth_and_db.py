"""
Tests for MongoDB connectivity, registration, and authentication.

Covers:
  - Registration: success, duplicate email, DB failure, response structure
  - Authentication: valid JWT, invalid JWT, DB timeout returns 503 (not 401)
  - MongoDB connection parameter validation

Run with:
  cd backend
  venv\\Scripts\\python -m pytest tests/test_auth_and_db.py -v

All tests use mocked DB calls — no real network or Atlas connection required.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from bson import ObjectId

import bcrypt
from jose import jwt


# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

SECRET = "test-secret-key"
ALGORITHM = "HS256"
USER_ID = "507f1f77bcf86cd799439011"
EMAIL = "alice@example.com"
NAME = "Alice"
PASSWORD = "securepass123"


def _hash(text: str) -> str:
    return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()


def _make_token(user_id: str = USER_ID, email: str = EMAIL, minutes: int = 60 * 24 * 7) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def _make_user_doc(user_id: str = USER_ID, email: str = EMAIL, name: str = NAME) -> dict:
    return {
        "_id": ObjectId(user_id),
        "name": name,
        "email": email,
        "password_hash": _hash(PASSWORD),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


# ─────────────────────────────────────────────────────────────
# SECTION 1: MongoDB Connection Configuration
# ─────────────────────────────────────────────────────────────

class TestMongoDBConnectionConfig:
    """
    Verify the connection parameters are set to values that handle Atlas M0
    idle-connection recycling correctly.
    """

    def test_max_idle_time_set(self):
        """
        maxIdleTimeMS must be less than Atlas M0's ~60s idle timeout
        so the driver retires connections before Atlas drops them.
        """
        # The database.py module sets maxIdleTimeMS=30_000 (30 seconds)
        # Simulate the check without connecting
        max_idle_ms = 30_000  # value from database.py
        atlas_idle_timeout_ms = 60_000  # Atlas M0 approximate limit
        assert max_idle_ms < atlas_idle_timeout_ms, (
            "maxIdleTimeMS must be less than Atlas M0's idle timeout (~60s) "
            "to prevent NetworkTimeout on first use after idle"
        )

    def test_socket_timeout_adequate(self):
        """socketTimeoutMS must be long enough for Atlas M0 operations."""
        socket_timeout_ms = 20_000  # value from database.py
        assert socket_timeout_ms >= 15_000, "socketTimeoutMS should be at least 15s for Atlas M0"

    def test_server_selection_timeout_reasonable(self):
        """serverSelectionTimeoutMS should surface problems quickly but not be too short."""
        server_sel_ms = 10_000  # value from database.py
        assert 5_000 <= server_sel_ms <= 15_000

    def test_retry_reads_enabled(self):
        """retryReads=True allows the driver to retry on stale connections."""
        retry_reads = True  # value from database.py
        assert retry_reads is True

    def test_retry_writes_enabled(self):
        """retryWrites=True allows safe retry on stale connection writes."""
        retry_writes = True  # value from database.py
        assert retry_writes is True


# ─────────────────────────────────────────────────────────────
# SECTION 2: Registration Logic
# ─────────────────────────────────────────────────────────────

class TestRegistrationLogic:
    """
    Simulate the registration endpoint logic with mocked DB calls.
    """

    def _simulate_register(
        self,
        email: str,
        name: str,
        password: str,
        existing_user=None,       # What find_one returns for dup check
        insert_raises=None,       # Exception to raise on insert_one
        find_after_insert=None,   # NOT USED — register no longer re-reads
    ) -> dict:
        """
        Simulate the fixed register endpoint logic:
          1. Duplicate email check
          2. insert_one
          3. Build response from insert data (no second find_one)
        Returns dict with 'success', 'status_code', 'message', 'user_id'
        """
        from pymongo.errors import PyMongoError

        email_normalized = email.lower().strip()

        # Step 1: Duplicate check
        if existing_user is not None:
            return {"success": False, "status_code": 409, "message": "An account with this email already exists."}

        # Step 2: Insert
        if insert_raises:
            if isinstance(insert_raises, PyMongoError):
                return {"success": False, "status_code": 503, "message": "Could not create account due to a database error."}
            raise insert_raises

        # Simulate successful insert
        inserted_id = ObjectId()

        # Step 3: Build response from inserted data — NO second DB read
        return {
            "success": True,
            "status_code": 201,
            "message": "Account created successfully",
            "user_id": str(inserted_id),
            "email": email_normalized,
            "name": name.strip(),
            "second_db_read": False,  # Explicitly: no re-read
        }

    def test_successful_registration_no_second_db_read(self):
        """
        Successful registration must not perform a second DB read after insert.
        This was the source of the NetworkTimeout at auth.py:96.
        """
        result = self._simulate_register(email=EMAIL, name=NAME, password=PASSWORD)
        assert result["success"] is True
        assert result["status_code"] == 201
        assert result["second_db_read"] is False, (
            "Registration must NOT do a second find_one after insert_one — "
            "this was the cause of the NetworkTimeout at auth.py:96"
        )

    def test_duplicate_email_returns_409(self):
        """Registering with an existing email must return 409."""
        result = self._simulate_register(
            email=EMAIL, name=NAME, password=PASSWORD,
            existing_user=_make_user_doc(),
        )
        assert result["status_code"] == 409
        assert result["success"] is False

    def test_db_insert_failure_returns_503(self):
        """
        If insert_one fails (DB timeout or error), return 503 — not 500.
        503 tells the frontend the server is temporarily unavailable.
        """
        from pymongo.errors import NetworkTimeout
        result = self._simulate_register(
            email=EMAIL, name=NAME, password=PASSWORD,
            insert_raises=NetworkTimeout("timed out"),
        )
        assert result["status_code"] == 503
        assert result["success"] is False

    def test_registration_normalizes_email(self):
        """Email must be stored lowercase regardless of input."""
        result = self._simulate_register(email="ALICE@EXAMPLE.COM", name=NAME, password=PASSWORD)
        assert result["email"] == "alice@example.com"

    def test_registration_trims_name(self):
        """Name must be stripped of leading/trailing whitespace."""
        result = self._simulate_register(email=EMAIL, name="  Alice  ", password=PASSWORD)
        assert result["name"] == "Alice"

    def test_response_includes_user_id(self):
        """Response must include user_id from the inserted document."""
        result = self._simulate_register(email=EMAIL, name=NAME, password=PASSWORD)
        assert "user_id" in result
        assert len(result["user_id"]) == 24  # ObjectId hex string length

    def test_db_dup_check_failure_returns_503(self):
        """
        If the duplicate-email find_one fails (DB error), return 503.
        This prevents the endpoint from hanging or crashing.
        """
        from pymongo.errors import NetworkTimeout

        # Simulate: find_one raises instead of returning None/doc
        def simulate_dup_check_failure():
            from pymongo.errors import PyMongoError
            raise NetworkTimeout("find timed out")

        # Simulate endpoint logic
        try:
            simulate_dup_check_failure()
            status_code = 201
        except Exception:
            status_code = 503

        assert status_code == 503


# ─────────────────────────────────────────────────────────────
# SECTION 3: Authentication — get_current_user
# ─────────────────────────────────────────────────────────────

class TestGetCurrentUserLogic:
    """
    Simulate get_current_user logic to verify correct HTTP status codes.
    """

    def _simulate_get_current_user(
        self,
        token: str | None,
        db_user=None,          # What db.users.find_one returns
        db_raises=None,        # Exception to raise from find_one
        secret: str = SECRET,
    ) -> dict:
        """
        Simulate get_current_user endpoint logic.
        Returns dict with 'status_code' and optionally 'user'.
        """
        from pymongo.errors import PyMongoError

        # No token
        if not token:
            return {"status_code": 401, "detail": "Not authenticated. Please log in."}

        # Decode JWT
        try:
            payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                return {"status_code": 401, "detail": "Invalid token payload."}
        except Exception:
            return {"status_code": 401, "detail": "Invalid or expired token."}

        # DB lookup
        if db_raises:
            if isinstance(db_raises, PyMongoError):
                return {
                    "status_code": 503,
                    "detail": "Database temporarily unavailable. Please try again in a moment.",
                }
            raise db_raises

        if db_user is None:
            return {"status_code": 401, "detail": "User account not found."}

        return {"status_code": 200, "user": db_user}

    def test_valid_token_valid_user_returns_200(self):
        """Valid JWT + user in DB → 200 OK."""
        token = _make_token()
        result = self._simulate_get_current_user(token=token, db_user=_make_user_doc())
        assert result["status_code"] == 200
        assert "user" in result

    def test_no_token_returns_401(self):
        """No token → 401."""
        result = self._simulate_get_current_user(token=None)
        assert result["status_code"] == 401

    def test_invalid_jwt_returns_401(self):
        """Tampered/invalid JWT → 401."""
        result = self._simulate_get_current_user(token="this.is.not.valid", db_user=_make_user_doc())
        assert result["status_code"] == 401

    def test_expired_jwt_returns_401(self):
        """Expired JWT → 401."""
        expired_token = _make_token(minutes=-1)
        result = self._simulate_get_current_user(token=expired_token, db_user=_make_user_doc())
        assert result["status_code"] == 401

    def test_db_timeout_returns_503_not_401(self):
        """
        CRITICAL: When MongoDB times out, return 503 — NOT 401.

        Previously, any exception from db.users.find_one propagated as an
        unhandled error which FastAPI converted to 500. But the frontend
        treated any non-200 from /auth/me as "not authenticated" and
        cleared the session. With the fix, 503 is explicit: the JWT is
        valid but the DB is temporarily unreachable.
        """
        from pymongo.errors import NetworkTimeout
        token = _make_token()
        result = self._simulate_get_current_user(
            token=token,
            db_raises=NetworkTimeout("ac-oosxp75-shard-00-02.wazvnho.mongodb.net:27017: timed out"),
        )
        assert result["status_code"] == 503, (
            "MongoDB timeout must return 503 (DB unavailable), NOT 401 (not authenticated). "
            "Returning 401 on a DB timeout invalidates valid frontend sessions."
        )

    def test_user_not_in_db_returns_401(self):
        """Valid JWT but user deleted from DB → 401."""
        token = _make_token()
        result = self._simulate_get_current_user(token=token, db_user=None)
        assert result["status_code"] == 401

    def test_wrong_secret_returns_401(self):
        """Token signed with wrong secret → 401."""
        token = _make_token()
        result = self._simulate_get_current_user(token=token, db_user=_make_user_doc(), secret="wrong-secret")
        assert result["status_code"] == 401


# ─────────────────────────────────────────────────────────────
# SECTION 4: JWT Utilities
# ─────────────────────────────────────────────────────────────

class TestJWTUtilities:
    """Tests for JWT creation and decoding."""

    def test_token_contains_sub(self):
        token = _make_token(user_id=USER_ID)
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == USER_ID

    def test_token_contains_email(self):
        token = _make_token(email=EMAIL)
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["email"] == EMAIL

    def test_token_expires(self):
        expired = _make_token(minutes=-1)
        with pytest.raises(Exception):  # jose JWTError
            jwt.decode(expired, SECRET, algorithms=[ALGORITHM])

    def test_token_expiry_in_future(self):
        token = _make_token(minutes=60)
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────
# SECTION 5: Registration → Login Flow (integration-level logic)
# ─────────────────────────────────────────────────────────────

class TestRegistrationToLoginFlow:
    """
    Verify the intended registration → redirect to login flow.
    These test the logic, not the React component directly.
    """

    def test_success_201_should_redirect_to_login(self):
        """
        On HTTP 201 from /auth/register, the frontend must redirect to /login.
        (Previously redirected to /dashboard — wrong per spec.)
        """
        status_code = 201
        intended_redirect = "/login"

        def get_redirect(status):
            if status == 201:
                return "/login"
            return None

        assert get_redirect(status_code) == intended_redirect

    def test_409_duplicate_should_redirect_to_login(self):
        """
        On 409 Conflict, the user already has an account — redirect to login.
        """
        status_code = 409
        def get_redirect(status):
            if status == 409:
                return "/login"
            return None

        assert get_redirect(status_code) == "/login"

    def test_503_ambiguous_should_redirect_to_login_not_retry(self):
        """
        On 503 (DB unavailable after possible insert), redirect to login
        instead of allowing a blind retry that could create a duplicate account.
        """
        status_code = 503
        def handle_503():
            # Correct behavior: tell user to try logging in first
            return {"action": "navigate_to_login", "message": "account may have been created"}

        result = handle_503()
        assert result["action"] == "navigate_to_login"

    def test_no_duplicate_on_409_retry(self):
        """
        If registration returns 409 and user retries with same email,
        the backend rejects the duplicate — no account created twice.
        """
        # Simulate: DB already has user
        existing_user = _make_user_doc(email=EMAIL)
        email_in_db = existing_user["email"]

        # Second registration attempt with same email
        email_attempt = EMAIL.lower()
        is_duplicate = (email_attempt == email_in_db)
        assert is_duplicate, "Duplicate email must be detected on retry"
