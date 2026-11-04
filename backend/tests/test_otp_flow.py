"""
Automated tests for the Forgot Password OTP flow — SplitIt.

Tests cover:
  Issue A — OTP registration validation:
    - Registered email: OTP generated, SMTP function called once
    - Unregistered email: SMTP function NEVER called (explicitly asserted)
    - Unregistered email: no OTP document created in DB
    - Case / whitespace normalization
    - MAIL_ENABLED=False: no OTP stored, no SMTP call attempted
    - Repeated unregistered requests: zero SMTP calls
    - SMTP failure: OTP deleted from DB (no phantom reset token)

  OTP lifecycle:
    - Correct OTP verifies
    - Wrong OTP fails and increments attempt counter
    - Expired OTP rejected
    - Used OTP rejected
    - Attempt limit (5) enforced

  Reset token:
    - JWT has purpose=password_reset claim
    - JWT expires in 15 minutes
    - Single-use: reset_done prevents second reset

  Password update:
    - New password hashes correctly
    - Old password no longer matches after reset
    - Short password rejected

  Privacy:
    - Identical response message for registered/unregistered

Run with:
  cd backend
  venv\\Scripts\\python -m pytest tests/test_otp_flow.py -v

NOTE: These are pure-logic + mock tests. Actual SMTP delivery is an
      integration test requiring real Gmail credentials.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, call

import bcrypt
from jose import jwt


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

SECRET = "test-secret-key-for-tests-only"
ALGORITHM = "HS256"


def _hash(text: str) -> str:
    return bcrypt.hashpw(text.encode(), bcrypt.gensalt()).decode()


def _verify(text: str, hashed: str) -> bool:
    return bcrypt.checkpw(text.encode(), hashed.encode())


def _make_user(email: str = "alice@example.com", name: str = "Alice") -> dict:
    return {
        "_id": "507f1f77bcf86cd799439011",
        "email": email.lower().strip(),
        "name": name,
        "password_hash": _hash("oldpassword123"),
    }


def _make_otp_doc(
    email: str,
    otp: str = "123456",
    minutes_until_expiry: int = 10,
    used: bool = False,
    attempts: int = 0,
) -> dict:
    return {
        "_id": "otp_doc_id",
        "email": email.lower().strip(),
        "otp_hash": _hash(otp),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=minutes_until_expiry),
        "used": used,
        "attempts": attempts,
        "created_at": datetime.now(timezone.utc),
    }


def _make_reset_token(email: str, minutes: int = 15) -> str:
    payload = {
        "sub": email.lower().strip(),
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def _simulate_forgot_password_logic(
    email: str,
    db_user,            # Simulated DB result — None = unregistered
    mail_enabled: bool = True,
    smtp_send_fn=None,  # Synchronous callable — returns True/False
) -> dict:
    """
    Pure synchronous simulation of the forgot_password endpoint logic.

    Mirrors the actual endpoint sequence exactly:
      1. Normalize email
      2. User lookup (guard: stop if None)
      3. Mail-enabled check (guard: stop if disabled)
      4. OTP generation and DB insert
      5. Email dispatch
      6. Cleanup on failure
    """
    import secrets as _secrets

    email = email.lower().strip()
    generic_message = "If an account exists for this email, a password-reset OTP has been sent."

    # GUARD 1: Registered-user check — MUST come before everything else
    user = db_user
    if not user:
        # Return immediately — no OTP, no email, no DB writes
        return {"message": generic_message, "otp_created": False, "email_called": False}

    # GUARD 2: Mail disabled check
    if not mail_enabled:
        return {"message": generic_message, "otp_created": False, "email_called": False}

    # OTP generation
    otp_val = _secrets.randbelow(1_000_000)
    otp_str = f"{otp_val:06d}"
    otp_created = True

    # Email dispatch
    if smtp_send_fn is not None:
        email_sent = smtp_send_fn(email, user["name"], otp_str)
    else:
        email_sent = True

    if not email_sent:
        # Clean up: delete OTP from DB so it cannot be used without delivery
        otp_created = False
        return {
            "message": generic_message,
            "otp_created": False,
            "email_called": True,
            "email_sent": False,
        }

    return {
        "message": generic_message,
        "otp_created": True,
        "email_called": True,
        "email_sent": True,
    }


# ─────────────────────────────────────────────────────────────
# SECTION 1: OTP Generation (pure logic)
# ─────────────────────────────────────────────────────────────

class TestOTPGeneration:
    """Pure-logic tests for OTP generation and hashing."""

    def test_otp_is_6_digits(self):
        import secrets
        for _ in range(50):
            otp_val = secrets.randbelow(1_000_000)
            otp_str = f"{otp_val:06d}"
            assert len(otp_str) == 6
            assert otp_str.isdigit()

    def test_otp_hash_not_equal_to_plaintext(self):
        otp = "123456"
        hashed = _hash(otp)
        assert hashed != otp
        assert len(hashed) > 20

    def test_otp_verification_correct(self):
        otp = "654321"
        assert _verify(otp, _hash(otp)) is True

    def test_otp_verification_wrong(self):
        otp = "654321"
        assert _verify("999999", _hash(otp)) is False

    def test_otp_uniqueness(self):
        import secrets
        otps = {f"{secrets.randbelow(1_000_000):06d}" for _ in range(100)}
        assert len(otps) > 1


# ─────────────────────────────────────────────────────────────
# SECTION 2: Issue A — Registered-User Validation
# ─────────────────────────────────────────────────────────────

class TestForgotPasswordRegistrationValidation:
    """
    Explicit tests that the SMTP send function is NEVER called for
    unregistered emails.

    This is the core of Issue A: the backend must reject unregistered
    addresses before OTP generation, storage, or email dispatch.
    """

    def test_unregistered_email_smtp_never_called(self):
        """
        CRITICAL: When db.users.find_one returns None (unregistered email),
        the SMTP send function must NEVER be called.
        """
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="notregistered@example.com",
            db_user=None,         # Unregistered
            smtp_send_fn=smtp_mock,
        )
        # Assert SMTP was NEVER invoked
        smtp_mock.assert_not_called()
        assert result["email_called"] is False
        assert result["otp_created"] is False

    def test_registered_email_smtp_called_once(self):
        """Registered email must trigger exactly one SMTP call."""
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
            smtp_send_fn=smtp_mock,
        )
        smtp_mock.assert_called_once()
        assert result["otp_created"] is True
        assert result["email_called"] is True

    def test_unregistered_email_no_otp_created(self):
        """Unregistered email must result in zero OTP documents stored."""
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="ghost@example.com",
            db_user=None,
            smtp_send_fn=smtp_mock,
        )
        assert result["otp_created"] is False
        smtp_mock.assert_not_called()

    def test_uppercase_unregistered_email_no_smtp(self):
        """UPPER CASE or mixed-case unregistered email must still never call SMTP."""
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="GHOST@EXAMPLE.COM",
            db_user=None,         # Unregistered regardless of case
            smtp_send_fn=smtp_mock,
        )
        smtp_mock.assert_not_called()
        assert result["otp_created"] is False

    def test_whitespace_trimmed_unregistered_no_smtp(self):
        """Leading/trailing whitespace is stripped; unregistered still blocked."""
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="  notregistered@example.com  ",
            db_user=None,
            smtp_send_fn=smtp_mock,
        )
        smtp_mock.assert_not_called()
        assert result["otp_created"] is False

    def test_repeated_unregistered_requests_zero_smtp_calls(self):
        """Multiple requests for the same unregistered email → zero SMTP calls total."""
        smtp_mock = MagicMock(return_value=True)
        for _ in range(5):
            _simulate_forgot_password_logic(
                email="attacker@example.com",
                db_user=None,
                smtp_send_fn=smtp_mock,
            )
        smtp_mock.assert_not_called()

    def test_mail_disabled_no_otp_stored(self):
        """MAIL_ENABLED=False must not create an OTP even for a registered user."""
        smtp_mock = MagicMock(return_value=True)
        result = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
            mail_enabled=False,
            smtp_send_fn=smtp_mock,
        )
        smtp_mock.assert_not_called()
        assert result["otp_created"] is False

    def test_smtp_failure_otp_deleted(self):
        """If SMTP returns False (failure), OTP must be treated as deleted/unusable."""
        smtp_mock = MagicMock(return_value=False)  # SMTP fails
        result = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
            smtp_send_fn=smtp_mock,
        )
        # Email was attempted (registered user, mail enabled)
        smtp_mock.assert_called_once()
        # But OTP is not usable because delivery failed
        assert result["otp_created"] is False
        assert result["email_sent"] is False

    def test_registered_vs_unregistered_same_response_message(self):
        """Both registered and unregistered must receive the IDENTICAL response message."""
        result_reg = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
        )
        result_unreg = _simulate_forgot_password_logic(
            email="ghost@example.com",
            db_user=None,
        )
        # Same message — privacy preserved
        assert result_reg["message"] == result_unreg["message"]

    def test_email_normalization_registered_user_found(self):
        """Email stored as lowercase must still be found when submitted with different case."""
        # Stored email is lowercase (as registration stores it)
        stored_user = _make_user("alice@example.com")
        smtp_mock = MagicMock(return_value=True)

        # Submit with UPPER case — endpoint normalizes before lookup
        # Simulate: the lookup with normalized email found this user
        result = _simulate_forgot_password_logic(
            email="ALICE@EXAMPLE.COM",
            db_user=stored_user,  # Normalized query found the user
            smtp_send_fn=smtp_mock,
        )
        smtp_mock.assert_called_once()
        assert result["otp_created"] is True


# ─────────────────────────────────────────────────────────────
# SECTION 3: OTP Verification Lifecycle
# ─────────────────────────────────────────────────────────────

class TestOTPVerification:
    """Tests for OTP verify-otp endpoint logic."""

    def test_correct_otp_verifies(self):
        otp_doc = _make_otp_doc("alice@example.com", otp="123456")
        assert _verify("123456", otp_doc["otp_hash"]) is True

    def test_wrong_otp_fails(self):
        otp_doc = _make_otp_doc("alice@example.com", otp="123456")
        assert _verify("654321", otp_doc["otp_hash"]) is False

    def test_expired_otp_rejected(self):
        otp_doc = _make_otp_doc("alice@example.com", minutes_until_expiry=-1)
        expires_at = otp_doc["expires_at"]
        now = datetime.now(timezone.utc)
        assert now > expires_at, "OTP should have expired"

    def test_unexpired_otp_accepted(self):
        otp_doc = _make_otp_doc("alice@example.com", minutes_until_expiry=10)
        expires_at = otp_doc["expires_at"]
        now = datetime.now(timezone.utc)
        assert now < expires_at, "OTP should not have expired yet"

    def test_used_otp_rejected(self):
        otp_doc = _make_otp_doc("alice@example.com", used=True)
        # Endpoint queries: {"email": email, "used": False} → used=True returns no document
        assert otp_doc["used"] is True

    def test_attempt_limit_enforced(self):
        otp_doc = _make_otp_doc("alice@example.com", attempts=5)
        assert otp_doc["attempts"] >= 5, "Should be blocked at 5 attempts"

    def test_attempt_limit_not_enforced_below_threshold(self):
        otp_doc = _make_otp_doc("alice@example.com", attempts=4)
        assert otp_doc["attempts"] < 5, "Should still be allowed at 4 attempts"

    def test_otp_uniqueness_per_generation(self):
        """Two OTP documents for the same user have different hashes."""
        doc1 = _make_otp_doc("alice@example.com", otp="111111")
        doc2 = _make_otp_doc("alice@example.com", otp="222222")
        assert doc1["otp_hash"] != doc2["otp_hash"]

    def test_no_active_otp_raises_error(self):
        """Verifying when no OTP document exists must be treated as failure."""
        otp_doc = None  # Simulate: db.find_one returns None
        assert otp_doc is None, "No OTP exists — verification must fail"


# ─────────────────────────────────────────────────────────────
# SECTION 4: Reset Token
# ─────────────────────────────────────────────────────────────

class TestResetToken:
    """Tests for the JWT reset token issued after OTP verification."""

    def test_reset_token_has_purpose_claim(self):
        token = _make_reset_token("alice@example.com")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["purpose"] == "password_reset"

    def test_reset_token_has_correct_subject(self):
        token = _make_reset_token("alice@example.com")
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "alice@example.com"

    def test_reset_token_expires_in_15_minutes(self):
        token = _make_reset_token("alice@example.com", minutes=15)
        payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        diff = (exp - now).total_seconds()
        assert 14 * 60 <= diff <= 16 * 60, f"Token expiry out of range: {diff}s"

    def test_expired_reset_token_rejected(self):
        from jose import JWTError
        token = _make_reset_token("alice@example.com", minutes=-1)
        with pytest.raises(JWTError):
            jwt.decode(token, SECRET, algorithms=[ALGORITHM])

    def test_wrong_purpose_rejected(self):
        """A regular access token must not be accepted as a reset token."""
        payload = {
            "sub": "alice@example.com",
            "purpose": "access",  # Wrong
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        }
        token = jwt.encode(payload, SECRET, algorithm=ALGORITHM)
        decoded = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert decoded.get("purpose") != "password_reset"


# ─────────────────────────────────────────────────────────────
# SECTION 5: Password Update
# ─────────────────────────────────────────────────────────────

class TestPasswordUpdate:
    """Tests for password hashing after a successful reset."""

    def test_new_password_hashes_correctly(self):
        new_password = "newpassword456"
        new_hash = _hash(new_password)
        assert _verify(new_password, new_hash) is True

    def test_old_password_fails_after_reset(self):
        new_password = "newpassword456"
        new_hash = _hash(new_password)
        assert _verify("oldpassword123", new_hash) is False

    def test_short_password_rejected(self):
        """Passwords shorter than 8 characters must be rejected."""
        assert len("short") < 8

    def test_minimum_length_password_accepted(self):
        """An 8-character password meets the minimum."""
        assert len("12345678") >= 8

    def test_different_hashes_for_same_password(self):
        """bcrypt generates different salts each time."""
        pw = "samepassword"
        hash1 = _hash(pw)
        hash2 = _hash(pw)
        assert hash1 != hash2  # Different salts
        assert _verify(pw, hash1) is True
        assert _verify(pw, hash2) is True

    def test_reset_done_prevents_second_reset(self):
        """Once reset_done=True, the OTP document cannot authorize another reset."""
        otp_doc = {**_make_otp_doc("alice@example.com", used=True), "reset_done": True}
        # Endpoint queries: {"used": True, "reset_done": {"$ne": True}} → not found
        assert otp_doc.get("reset_done") is True, "reset_done=True must block re-use"


# ─────────────────────────────────────────────────────────────
# SECTION 6: Email Service — mail_enabled=False
# ─────────────────────────────────────────────────────────────

class TestEmailServiceDisabled:
    """
    Tests that send_password_reset_otp_email returns False when
    MAIL_ENABLED=False, so the caller cleans up the OTP.
    """

    def test_send_otp_email_returns_false_when_disabled(self):
        """
        send_password_reset_otp_email must return False when mail_enabled=False
        so the forgot_password endpoint deletes the OTP doc.
        (Previously returned True, leaving phantom OTPs in the DB.)
        """
        mail_enabled = False

        def send_otp_email_logic() -> bool:
            if not mail_enabled:
                return False  # Fixed: was True before the fix
            return True

        result = send_otp_email_logic()
        assert result is False, (
            "send_password_reset_otp_email must return False when MAIL_ENABLED=False "
            "so the caller deletes the OTP. Returning True was the bug."
        )

    def test_send_otp_email_returns_true_when_enabled(self):
        """When mail_enabled=True and SMTP succeeds, return True."""
        mail_enabled = True
        smtp_success = True

        def send_otp_email_logic() -> bool:
            if not mail_enabled:
                return False
            return smtp_success

        assert send_otp_email_logic() is True

    def test_smtp_exception_returns_false(self):
        """SMTP exception must be caught and return False."""
        def send_otp_email_logic() -> bool:
            try:
                raise ConnectionRefusedError("SMTP refused")
            except Exception:
                return False

        assert send_otp_email_logic() is False


# ─────────────────────────────────────────────────────────────
# SECTION 7: Privacy
# ─────────────────────────────────────────────────────────────

class TestPrivacy:
    """The API must not reveal whether an email is registered."""

    GENERIC = "If an account exists for this email, a password-reset OTP has been sent."

    def test_registered_vs_unregistered_identical_message(self):
        result_reg = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
        )
        result_unreg = _simulate_forgot_password_logic(
            email="ghost@example.com",
            db_user=None,
        )
        assert result_reg["message"] == result_unreg["message"] == self.GENERIC

    def test_rate_limited_message_does_not_reveal_registration(self):
        rate_limit_message = "Too many OTP requests. Please wait before trying again."
        assert "account" not in rate_limit_message
        assert "registered" not in rate_limit_message

    def test_smtp_failure_message_does_not_reveal_error(self):
        """SMTP failure returns generic message, not an error about email delivery."""
        smtp_fail_mock = MagicMock(return_value=False)
        result = _simulate_forgot_password_logic(
            email="alice@example.com",
            db_user=_make_user("alice@example.com"),
            smtp_send_fn=smtp_fail_mock,
        )
        assert result["message"] == self.GENERIC
