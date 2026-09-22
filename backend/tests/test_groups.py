"""
Tests for Group and Member API endpoints.

Covers US-01, US-02, US-03 acceptance criteria.
"""

import pytest
from fastapi.testclient import TestClient


class TestCreateGroup:
    """US-01: Create a group."""

    def test_create_group_success(self, client: TestClient):
        """Creating a group returns 201 with the group data."""
        response = client.post("/api/v1/groups/", json={"name": "Trip to Goa"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Trip to Goa"
        assert data["id"] is not None
        assert data["member_count"] == 0

    def test_create_group_with_description(self, client: TestClient):
        """Group can optionally have a description."""
        response = client.post(
            "/api/v1/groups/",
            json={"name": "Flat 4B", "description": "Monthly flat expenses"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["description"] == "Monthly flat expenses"

    def test_create_group_empty_name_rejected(self, client: TestClient):
        """Empty group name is rejected with 422."""
        response = client.post("/api/v1/groups/", json={"name": ""})
        assert response.status_code == 422

    def test_create_group_blank_name_rejected(self, client: TestClient):
        """Whitespace-only group name is rejected."""
        response = client.post("/api/v1/groups/", json={"name": "   "})
        assert response.status_code == 422

    def test_list_groups_empty(self, client: TestClient):
        """Listing groups on an empty DB returns empty list."""
        response = client.get("/api/v1/groups/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_groups_shows_created(self, client: TestClient):
        """Created group appears in the list."""
        client.post("/api/v1/groups/", json={"name": "Dinner Club"})
        response = client.get("/api/v1/groups/")
        assert response.status_code == 200
        groups = response.json()
        assert len(groups) == 1
        assert groups[0]["name"] == "Dinner Club"

    def test_get_group_not_found(self, client: TestClient):
        """Getting a non-existent group returns 404."""
        response = client.get("/api/v1/groups/9999")
        assert response.status_code == 404

    def test_delete_group(self, client: TestClient):
        """Deleting a group removes it."""
        create_resp = client.post("/api/v1/groups/", json={"name": "To Delete"})
        group_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/api/v1/groups/{group_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/api/v1/groups/{group_id}")
        assert get_resp.status_code == 404


class TestAddMembers:
    """US-02, US-03: Add and view group members."""

    def _create_group(self, client: TestClient, name: str = "Test Group") -> int:
        resp = client.post("/api/v1/groups/", json={"name": name})
        return resp.json()["id"]

    def test_add_member_success(self, client: TestClient):
        """Adding a member returns 201 with member data."""
        group_id = self._create_group(client)
        response = client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"name": "Rahul"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Rahul"
        assert data["group_id"] == group_id

    def test_add_member_empty_name_rejected(self, client: TestClient):
        """Empty member name is rejected."""
        group_id = self._create_group(client)
        response = client.post(
            f"/api/v1/groups/{group_id}/members",
            json={"name": ""},
        )
        assert response.status_code == 422

    def test_add_duplicate_member_rejected(self, client: TestClient):
        """Duplicate member name in the same group is rejected with 409."""
        group_id = self._create_group(client)
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Aman"})
        response = client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Aman"})
        assert response.status_code == 409

    def test_add_duplicate_member_case_insensitive(self, client: TestClient):
        """Duplicate check is case-insensitive."""
        group_id = self._create_group(client)
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Priya"})
        response = client.post(f"/api/v1/groups/{group_id}/members", json={"name": "priya"})
        assert response.status_code == 409

    def test_add_member_to_nonexistent_group(self, client: TestClient):
        """Adding a member to a non-existent group returns 404."""
        response = client.post("/api/v1/groups/9999/members", json={"name": "Raj"})
        assert response.status_code == 404

    def test_list_members(self, client: TestClient):
        """Members are listed alphabetically."""
        group_id = self._create_group(client)
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Zara"})
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Aditya"})
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Maya"})

        response = client.get(f"/api/v1/groups/{group_id}/members")
        assert response.status_code == 200
        names = [m["name"] for m in response.json()]
        assert names == ["Aditya", "Maya", "Zara"]

    def test_group_detail_includes_members(self, client: TestClient):
        """GET /groups/{id} includes the member list."""
        group_id = self._create_group(client)
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Aditya"})
        client.post(f"/api/v1/groups/{group_id}/members", json={"name": "Rahul"})

        response = client.get(f"/api/v1/groups/{group_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["member_count"] == 2
        assert len(data["members"]) == 2

    def test_remove_member(self, client: TestClient):
        """Removing a member reduces the member count."""
        group_id = self._create_group(client)
        add_resp = client.post(
            f"/api/v1/groups/{group_id}/members", json={"name": "Kiran"}
        )
        member_id = add_resp.json()["id"]

        delete_resp = client.delete(f"/api/v1/groups/{group_id}/members/{member_id}")
        assert delete_resp.status_code == 204

        members_resp = client.get(f"/api/v1/groups/{group_id}/members")
        assert members_resp.json() == []

    def test_same_name_different_groups_allowed(self, client: TestClient):
        """The same member name can exist in different groups."""
        group1_id = self._create_group(client, "Group 1")
        group2_id = self._create_group(client, "Group 2")

        r1 = client.post(f"/api/v1/groups/{group1_id}/members", json={"name": "Alex"})
        r2 = client.post(f"/api/v1/groups/{group2_id}/members", json={"name": "Alex"})

        assert r1.status_code == 201
        assert r2.status_code == 201
