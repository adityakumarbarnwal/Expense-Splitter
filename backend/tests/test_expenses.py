"""
Tests for the Expense API endpoints.

Covers US-04, US-05 acceptance criteria.
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient


def create_group_with_members(client: TestClient) -> dict:
    """Helper: create a group with 3 members, return group_id and member_ids."""
    group_resp = client.post("/api/v1/groups/", json={"name": "Test Group"})
    group_id = group_resp.json()["id"]

    members = {}
    for name in ["Aditya", "Rahul", "Aman"]:
        resp = client.post(f"/api/v1/groups/{group_id}/members", json={"name": name})
        members[name] = resp.json()["id"]

    return {"group_id": group_id, "members": members}


class TestCreateExpense:
    """US-04: Add an expense."""

    def test_create_expense_success(self, client: TestClient):
        """Creating an expense returns 201 with calculated shares."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Dinner",
                "amount": 900,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"], members["Rahul"], members["Aman"]],
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Dinner"
        assert Decimal(str(data["amount"])) == Decimal("900.00")
        assert data["payer_id"] == members["Aditya"]
        assert len(data["participants"]) == 3

    def test_expense_shares_sum_to_total(self, client: TestClient):
        """Participant shares must sum to the total amount."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Groceries",
                "amount": 100,
                "payer_id": members["Rahul"],
                "participant_ids": list(members.values()),
            },
        )
        assert response.status_code == 201
        data = response.json()
        shares_sum = sum(Decimal(str(p["share"])) for p in data["participants"])
        assert shares_sum == Decimal("100.00"), f"Shares {shares_sum} != 100"

    def test_expense_rounding_three_people(self, client: TestClient):
        """₹100 / 3 people: last share absorbs the extra paisa."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Coffee",
                "amount": 100,
                "payer_id": members["Aditya"],
                "participant_ids": sorted(list(members.values())),
            },
        )
        data = response.json()
        shares = sorted(
            [Decimal(str(p["share"])) for p in data["participants"]]
        )
        # Two shares of 33.33, one of 33.34
        assert shares.count(Decimal("33.33")) == 2
        assert shares.count(Decimal("33.34")) == 1
        assert sum(shares) == Decimal("100.00")

    def test_expense_invalid_payer_rejected(self, client: TestClient):
        """Payer not in group is rejected with 400."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Taxi",
                "amount": 200,
                "payer_id": 99999,  # Non-existent member
                "participant_ids": list(members.values()),
            },
        )
        assert response.status_code == 400

    def test_expense_invalid_participant_rejected(self, client: TestClient):
        """Participant not in group is rejected with 400."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Taxi",
                "amount": 200,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"], 99999],  # 99999 not in group
            },
        )
        assert response.status_code == 400

    def test_expense_zero_amount_rejected(self, client: TestClient):
        """Zero amount is rejected by schema validation."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Nothing",
                "amount": 0,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"]],
            },
        )
        assert response.status_code == 422

    def test_expense_negative_amount_rejected(self, client: TestClient):
        """Negative amount is rejected."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Refund",
                "amount": -100,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"]],
            },
        )
        assert response.status_code == 422

    def test_expense_duplicate_participants_rejected(self, client: TestClient):
        """Duplicate participant IDs are rejected."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Lunch",
                "amount": 300,
                "payer_id": members["Aditya"],
                "participant_ids": [members["Aditya"], members["Aditya"]],  # Duplicate
            },
        )
        assert response.status_code == 422

    def test_list_expenses(self, client: TestClient):
        """Listed expenses are in reverse chronological order."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        for desc in ["Breakfast", "Lunch", "Dinner"]:
            client.post(
                f"/api/v1/groups/{group_id}/expenses",
                json={
                    "description": desc,
                    "amount": 100,
                    "payer_id": members["Aditya"],
                    "participant_ids": [members["Aditya"]],
                },
            )

        response = client.get(f"/api/v1/groups/{group_id}/expenses")
        assert response.status_code == 200
        descriptions = [e["description"] for e in response.json()]
        assert descriptions[0] == "Dinner"  # Most recent first

    def test_single_participant_expense(self, client: TestClient):
        """Single-participant expense: share equals full amount."""
        setup = create_group_with_members(client)
        group_id = setup["group_id"]
        members = setup["members"]

        response = client.post(
            f"/api/v1/groups/{group_id}/expenses",
            json={
                "description": "Solo taxi",
                "amount": 250,
                "payer_id": members["Rahul"],
                "participant_ids": [members["Rahul"]],
            },
        )
        data = response.json()
        assert len(data["participants"]) == 1
        assert Decimal(str(data["participants"][0]["share"])) == Decimal("250.00")
