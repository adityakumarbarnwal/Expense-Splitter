"""
FastAPI application factory — MongoDB + JWT Auth edition.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import connect_db, disconnect_db
from app.api.v1.router import router as api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Connect to MongoDB on startup, disconnect on shutdown."""
    logger.info("Starting up Group Expense Splitter API v2 (MongoDB)...")
    await connect_db()
    logger.info("Ready to serve requests.")
    yield
    await disconnect_db()
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Group Expense Splitter — DSC4141 Academic GenAI Project. MongoDB + JWT Auth.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router)


@app.get("/", tags=["health"])
def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": "mongodb",
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    return {
        "status": "healthy",
        "database": "mongodb",
        "db_name": settings.mongodb_db_name,
        "ai_configured": bool(settings.gemini_api_key),
    }
