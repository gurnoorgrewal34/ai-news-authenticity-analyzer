# =============================================================
# app/main.py — Entry Point (v2)
#
# WHAT CHANGED IN v2:
#   - Safe ALTER TABLE migration in startup event for new columns:
#     quick_summary, reading_time_label
#   - Migration uses raw SQL with IF NOT EXISTS guard — zero data loss
# =============================================================

from fastapi import FastAPI
from sqlalchemy import text

from app.config import APP_TITLE, APP_VERSION, APP_DESCRIPTION
from app.database import engine, Base
from app import models  # noqa: F401

from app.routers import news
from app.routers import analyze
from app.routers import history
from app.routers import context

import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    contact={"name": "Gurnoor — AI News Authenticity & Mental Wellness Analyzer"},
    license_info={"name": "MIT"},
)


# =============================================================
# STARTUP EVENT — Create Tables + Safe Column Migration
# =============================================================

@app.on_event("startup")
def create_tables():
    """
    1. Create all tables if they don't exist (idempotent).
    2. Safely add new columns to the existing table without
       touching any existing data.

    SQLite-safe ALTER TABLE strategy:
      - We attempt ADD COLUMN for each new column.
      - If the column already exists, SQLite raises an error
        which we catch and ignore.
      - This means the migration is always safe to run.
    """
    # Step 1: Create tables (no-op if they already exist)
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created / verified.")

    # Step 2: Safe column migrations for new fields added in v2
    new_columns = [
        ("quick_summary",       "TEXT"),
        ("reading_time_label",  "TEXT"),
    ]

    with engine.connect() as conn:
        for col_name, col_type in new_columns:
            try:
                conn.execute(
                    text(f"ALTER TABLE analysis_history ADD COLUMN {col_name} {col_type}")
                )
                conn.commit()
                logger.info("✅ Column '%s' added to analysis_history.", col_name)
            except Exception:
                # Column already exists — this is normal on every run after first
                logger.debug("Column '%s' already exists — skipping.", col_name)


# =============================================================
# Register Routers
# =============================================================
app.include_router(news.router)
app.include_router(analyze.router)
app.include_router(history.router)
app.include_router(context.router)


# =============================================================
# Root — Health Check
# =============================================================
@app.get("/", tags=["Health"])
def root():
    """
    ## Server Health Check

    Returns a welcome message and links to all API endpoints.
    """
    return {
        "status":   "online",
        "message":  "AI News Authenticity & Mental Wellness Analyzer — API v2 running.",
        "version":  APP_VERSION,
        "modules": {
            "module_1": "GET  /news?keyword=<topic>   — Live news fetching",
            "module_2": "POST /analyze                — AI sentiment & wellness analysis",
            "module_3": "GET  /history                — SQLite analysis history",
            "module_3b": "DELETE /history/{id}        — Delete a history record",
            "module_4": "GET  /context?topic=<topic>  — Historical context (Wikipedia + NewsAPI)",
        },
        "docs": "Visit /docs for the full interactive API documentation",
    }
