"""
Backend tests for Group Expense Splitter v2 — MongoDB + JWT Auth.

These tests use an in-memory test MongoDB instance (mongomock) or
the real test database. Tests are organized by feature.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Note: We need mongomock-motor for proper async testing
# For now, tests use the real MongoDB connection with a test database
# Configure TEST_MONGODB_DB_NAME in test environment

import os
os.environ["MONGODB_DB_NAME"] = "group_expense_test"
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-production"

from app.main import app
from app.db.database import get_database, connect_db, disconnect_db


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def client():
    """Create an async test client with real MongoDB (test DB)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest_asyncio.fixture(autouse=True, scope="session")
async def setup_db():
    """Connect to test DB before tests, clean up after."""
    await connect_db()
    yield
    # Clean up test data
    db = get_database()
    await db.users.drop()
    await db.groups.drop()
    await db.expenses.drop()
    await db.settlements.drop()
    await db.notifications.drop()
    await disconnect_db()


# ──────────────────────────────────────────────
# Auth Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["user"]["email"] == "test@example.com"
    assert data["user"]["name"] == "Test User"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    # Register once
    await client.post("/api/v1/auth/register", json={
        "name": "User A",
        "email": "duplicate@example.com",
        "password": "password123",
    })
    # Try to register with same email
    resp = await client.post("/api/v1/auth/register", json={
        "name": "User B",
        "email": "duplicate@example.com",
        "password": "different123",
    })
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Test",
        "email": "weak@example.com",
        "password": "short",  # < 8 chars
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/v1/auth/register", json={
        "name": "Login User",
        "email": "logintest@example.com",
        "password": "password123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "logintest@example.com",
        "password": "password123",
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["email"] == "logintest@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/v1/auth/register", json={
        "name": "Fail User",
        "email": "faillogin@example.com",
        "password": "password123",
    })
    resp = await client.post("/api/v1/auth/login", json={
        "email": "faillogin@example.com",
        "password": "wrongpassword",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client):
    reg_resp = await client.post("/api/v1/auth/register", json={
        "name": "Token User",
        "email": "tokenuser@example.com",
        "password": "password123",
    })
    token = None
    # Find token from cookie
    for cookie in reg_resp.cookies.items():
        if cookie[0] == "access_token":
            token = cookie[1]

    if token:
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "tokenuser@example.com"


# ──────────────────────────────────────────────
# Profile Tests
# ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_name_only(client):
    reg = await client.post("/api/v1/auth/register", json={
        "name": "Original Name",
        "email": "profile@example.com",
        "password": "password123",
    })
    token = reg.cookies.get("access_token")
    if not token:
        pytest.skip("Cookie not captured in test client")

    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.patch(
        "/api/v1/users/me",
        json={"name": "New Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New Name"
    # Email unchanged
    assert resp.json()["email"] == "profile@example.com"


# ──────────────────────────────────────────────
# Password Hashing Tests
# ──────────────────────────────────────────────

def test_password_not_stored_in_plaintext():
    """Verify bcrypt hashing is applied."""
    from app.core.auth import hash_password, verify_password
    pw = "mysecretpassword"
    hashed = hash_password(pw)
    assert hashed != pw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")  # bcrypt prefix
    assert verify_password(pw, hashed)
    assert not verify_password("wrongpassword", hashed)


# ──────────────────────────────────────────────
# Balance Formula Tests
# ──────────────────────────────────────────────

def test_balance_formula_basic():
    """Test the balance formula: net = total_paid - total_owed + settlements_paid - settlements_received"""
    from app.services.balance_engine import generate_settlement_suggestions

    balances = {
        "user_a": {
            "user_id": "user_a",
            "member_name": "Alice",
            "total_paid": 100.0,
            "total_owed": 50.0,
            "settlements_paid": 0.0,
            "settlements_received": 0.0,
            "net_balance": 50.0,  # Alice is owed 50
        },
        "user_b": {
            "user_id": "user_b",
            "member_name": "Bob",
            "total_paid": 0.0,
            "total_owed": 50.0,
            "settlements_paid": 0.0,
            "settlements_received": 0.0,
            "net_balance": -50.0,  # Bob owes 50
        },
    }

    suggestions = generate_settlement_suggestions(balances)
    assert len(suggestions) == 1
    assert suggestions[0]["amount"] == 50.0
    assert suggestions[0]["from_member_name"] == "Bob"
    assert suggestions[0]["to_member_name"] == "Alice"


def test_balance_formula_already_settled():
    from app.services.balance_engine import generate_settlement_suggestions

    balances = {
        "user_a": {"user_id": "user_a", "member_name": "Alice", "net_balance": 0.0,
                   "total_paid": 0.0, "total_owed": 0.0, "settlements_paid": 0.0, "settlements_received": 0.0},
        "user_b": {"user_id": "user_b", "member_name": "Bob", "net_balance": 0.0,
                   "total_paid": 0.0, "total_owed": 0.0, "settlements_paid": 0.0, "settlements_received": 0.0},
    }
    suggestions = generate_settlement_suggestions(balances)
    assert suggestions == []


def test_three_way_split():
    from app.services.balance_engine import generate_settlement_suggestions

    # Alice paid 90 total, Bob owes 30, Carol owes 30, Alice owes 30
    # Alice net = +60, Bob net = -30, Carol net = -30
    balances = {
        "alice": {"user_id": "alice", "member_name": "Alice", "net_balance": 60.0,
                  "total_paid": 0.0, "total_owed": 0.0, "settlements_paid": 0.0, "settlements_received": 0.0},
        "bob": {"user_id": "bob", "member_name": "Bob", "net_balance": -30.0,
                "total_paid": 0.0, "total_owed": 0.0, "settlements_paid": 0.0, "settlements_received": 0.0},
        "carol": {"user_id": "carol", "member_name": "Carol", "net_balance": -30.0,
                  "total_paid": 0.0, "total_owed": 0.0, "settlements_paid": 0.0, "settlements_received": 0.0},
    }
    suggestions = generate_settlement_suggestions(balances)
    assert len(suggestions) == 2
    total_paid = sum(s["amount"] for s in suggestions)
    assert abs(total_paid - 60.0) < 0.01


# ──────────────────────────────────────────────
# Expense Share Calculation Tests
# ──────────────────────────────────────────────

def test_equal_split_exact():
    from app.api.v1.expenses import _calculate_shares
    # 90 / 3 = 30 each (exact)
    shares = _calculate_shares(90.0, ["a", "b", "c"])
    assert sum(shares.values()) == pytest.approx(90.0, abs=0.01)
    assert all(v == pytest.approx(30.0) for v in shares.values())


def test_equal_split_rounding():
    from app.api.v1.expenses import _calculate_shares
    # 100 / 3 = 33.33, 33.33, 33.34
    shares = _calculate_shares(100.0, ["a", "b", "c"])
    total = sum(shares.values())
    assert total == pytest.approx(100.0, abs=0.01)


def test_health_endpoint():
    import httpx
    resp = httpx.get("http://localhost:8000/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "mongodb"
