"""API v1 router — aggregates all route modules."""

from fastapi import APIRouter
from app.api.v1 import groups, expenses, balances, ai

router = APIRouter(prefix="/api/v1")

router.include_router(groups.router)
router.include_router(expenses.router)
router.include_router(balances.router)
router.include_router(ai.router)
