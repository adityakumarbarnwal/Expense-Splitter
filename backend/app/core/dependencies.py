"""
FastAPI dependencies — MongoDB edition.

get_db() is no longer used (routes use get_database() directly from db.database).
This module is kept for potential future use.
"""

from app.db.database import get_database

__all__ = ["get_database"]
