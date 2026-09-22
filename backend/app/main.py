"""
FastAPI application factory.

Initializes the app, configures CORS, includes all routes,
and creates the database tables on startup.
"""

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.database import engine
from app.models import Base  # Import all models to register them with metadata
from app.api.v1.router import router as api_v1_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Creates all database tables on startup.
    (In production, use Alembic migrations instead.)
    """
    logger.info("Starting up Group Expense Splitter API...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A group expense splitting application with natural-language AI expense entry. "
        "Built for DSC4141 academic project."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_v1_router)


@app.get("/", tags=["health"])
def health_check() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health", tags=["health"])
def health() -> dict:
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "ai_configured": bool(
            settings.gemini_api_key
            and settings.gemini_api_key != "your_gemini_api_key_here"
        ),
    }
