"""
Pytest configuration for backend v2 tests (MongoDB).
"""
import os
import pytest

# Use a separate test database
os.environ.setdefault("MONGODB_DB_NAME", "group_expense_test")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-production")
