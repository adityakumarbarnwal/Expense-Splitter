"""
API v1 Router — collects all route modules.
"""

from fastapi import APIRouter
from app.api.v1 import auth, users, groups, expenses, balances, notifications, ai, dashboard

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(groups.router)
router.include_router(expenses.router)
router.include_router(balances.router)
router.include_router(notifications.router)
router.include_router(ai.router)
router.include_router(dashboard.router)
