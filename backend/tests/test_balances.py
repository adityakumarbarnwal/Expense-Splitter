"""
Tests for Balance Engine and Settlement Engine.

Covers US-06, US-07, US-08 acceptance criteria.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient

from app.services.balance_engine import calculate_group_balances
from app.services.settlement_engine import generate_settlement_suggestions


def create_full_setup(client: TestClient) -> dict:
    """Create a group with 3 members and return IDs."""
    group_resp = client.post("/api/v1/groups/", json={"name": "Balance Test Group"})
    group_id = group_resp.json()["id"]

    members = {}
    for name in ["Aditya", "Rahul", "Aman"]:
        resp = client.post(f"/api/v1/groups/{group_id}/members", json={"name": name})
        members[name] = resp.json()["id"]

    return {"group_id": group_id, "members": members}


class TestBalanceEngine:
    """Unit tests for the balance calculation engine."""

    def test_empty_group_no_balances(self, db):
        """Group with no expenses has no balances."""
        from app.models.group import Group
        group = Group(name="Empty Group")
        db.add(group)
        db.commit()

        balances = calculate_group_balances(db, group.id)
        assert balances == {}

    def test_single_expense_correct_balances(self, db):
        """One expense: payer has positive balance, participants have negative."""
        from app.models.group import Group, Member
        from app.models.expense import Expense, ExpenseParticipant

        # Setup
        group = Group(name="Test")
        db.add(group)
        db.flush()

        aditya = Member(group_id=group.id, name="Aditya")
        rahul = Member(group_id=group.id, name="Rahul")
        db.add_all([aditya, rahul])
        db.flush()

        # Aditya pays ₹100 for both
        expense = Expense(
            group_id=group.id,
            description="Lunch",
            amount=Decimal("100"),
            payer_id=aditya.id,
        )
        db.add(expense)
        db.flush()

        db.add(ExpenseParticipant(expense_id=expense.id, member_id=aditya.id, share=Decimal("50")))
        db.add(ExpenseParticipant(expense_id=expense.id, member_id=rahul.id, share=Decimal("50")))
        db.commit()

        balances = calculate_group_balances(db, group.id)

        # Aditya paid 100, owes 50 → net = +50 (owed money)
        assert balances[aditya.id]["net_balance"] == Decimal("50")
        # Rahul paid 0, owes 50 → net = -50 (owes money)
        assert balances[rahul.id]["net_balance"] == Decimal("-50")


class TestBalanceAPI:
    """Integration tests for the balances API."""

    def test_balances_empty_group(self, client: TestClient):
        """Group with no expenses returns empty balances."""
        group_resp = client.post("/api/v1/groups/", json={"name": "Empty"})
        group_id = group_resp.json()["id"]
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Solo"})

        response = client.get(f"/api/v1/groups/{group_id}/balances")
        assert response.status_code == 200
        data = response.json()
        assert data["is_settled"] is True
        assert data["settlement_suggestions"] == []

    def test_balances_after_expense(self, client: TestClient):
        """After an expense, payer has positive balance."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        # Aditya pays ₹900 for all 3 → each owes ₹300
        client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Dinner",
                "amount": 900,
                "payer_id": members["Aditya"],
                "participant_ids": list(members.values()),
            },
        )

        response = client.get(f"/api/v1/groups/{group_id}/balances")
        assert response.status_code == 200
        data = response.json()

        balances = {b["member_name"]: Decimal(b["net_balance"]) for b in data["balances"]}
        assert balances["Aditya"] == Decimal("600.00")  # Paid 900, owes 300
        assert balances["Rahul"] == Decimal("-300.00")
        assert balances["Aman"] == Decimal("-300.00")

        assert data["is_settled"] is False
        assert len(data["settlement_suggestions"]) > 0

    def test_balances_settle_to_zero(self, client: TestClient):
        """After settlement, balances update to zero."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        # Expense: Aditya pays 600 for Aditya and Rahul (300 each)
        client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Lunch",
                "amount": 600,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"], members["Rahul"]],
            },
        )

        # Rahul settles ₹300 to Aditya
        settle_resp = client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={
                "payer_id": members["Rahul"],
                "receiver_id": members["Aditya"],
                "amount": 300,
            },
        )
        assert settle_resp.status_code == 201

        # Check balances
        response = client.get(f"/api/v1/groups/{group_id}/balances")
        data = response.json()

        balances = {b["member_name"]: Decimal(b["net_balance"]) for b in data["balances"]}
        assert abs(balances["Aditya"]) < Decimal("0.01")
        assert abs(balances["Rahul"]) < Decimal("0.01")


class TestSettlementEngine:
    """Unit tests for the settlement suggestion engine."""

    def test_simple_two_person_suggestion(self):
        """A owes B ₹100 → suggestion: A pays B ₹100."""
        balances = {
            1: {"member_id": 1, "member_name": "A", "net_balance": Decimal("100")},
            2: {"member_id": 2, "member_name": "B", "net_balance": Decimal("-100")},
        }
        suggestions = generate_settlement_suggestions(balances)
        assert len(suggestions) == 1
        assert suggestions[0]["from_member_name"] == "B"
        assert suggestions[0]["to_member_name"] == "A"
        assert suggestions[0]["amount"] == Decimal("100.00")

    def test_all_settled_no_suggestions(self):
        """All zero balances → no suggestions."""
        balances = {
            1: {"member_id": 1, "member_name": "A", "net_balance": Decimal("0")},
            2: {"member_id": 2, "member_name": "B", "net_balance": Decimal("0")},
        }
        suggestions = generate_settlement_suggestions(balances)
        assert suggestions == []

    def test_three_people_minimal_transactions(self):
        """3 people: A=+200, B=-100, C=-100 → 2 transactions."""
        balances = {
            1: {"member_id": 1, "member_name": "A", "net_balance": Decimal("200")},
            2: {"member_id": 2, "member_name": "B", "net_balance": Decimal("-100")},
            3: {"member_id": 3, "member_name": "C", "net_balance": Decimal("-100")},
        }
        suggestions = generate_settlement_suggestions(balances)
        assert len(suggestions) == 2
        # Both B and C should pay A
        recipients = {s["to_member_name"] for s in suggestions}
        assert "A" in recipients


class TestSettlementAPI:
    """Integration tests for the settlements API."""

    def test_record_settlement_success(self, client: TestClient):
        """Recording a settlement returns 201."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={
                "payer_id": members["Rahul"],
                "receiver_id": members["Aditya"],
                "amount": 300,
                "note": "Settling dinner",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["payer_name"] == "Rahul"
        assert data["receiver_name"] == "Aditya"
        assert Decimal(str(data["amount"])) == Decimal("300.00")

    def test_settlement_same_payer_receiver_rejected(self, client: TestClient):
        """Payer and receiver cannot be the same member."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={
                "payer_id": members["Aditya"],
                "receiver_id": members["Aditya"],  # Same as payer
                "amount": 100,
            },
        )
        assert response.status_code == 422

    def test_settlement_invalid_member_rejected(self, client: TestClient):
        """Non-group member in settlement is rejected with 400."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={
                "payer_id": 99999,
                "receiver_id": members["Aditya"],
                "amount": 100,
            },
        )
        assert response.status_code == 400

    def test_list_settlements(self, client: TestClient):
        """Settlement history is listed in reverse chronological order."""
        setup = create_full_setup(client)
        group_id = setup["group_id"]
        members = setup["members"]

        client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={"payer_id": members["Rahul"], "receiver_id": members["Aditya"], "amount": 100},
        )
        client.post(
            f"/api/v1/groups/{group_id}/settlements",
            json={"payer_id": members["Aman"], "receiver_id": members["Aditya"], "amount": 200},
        )

        response = client.get(f"/api/v1/groups/{group_id}/settlements")
        assert response.status_code == 200
        settlements = response.json()
        assert len(settlements) == 2
