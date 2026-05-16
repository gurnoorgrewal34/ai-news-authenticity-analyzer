# =============================================================
# app/main.py — Entry Point of the FastAPI Application
#
# This file is the "hub" of the entire backend.
# It creates the server, imports all config, and registers
# every router (route group) that the API exposes.
#
# Current Modules:
#   Module 1 — /news    → Fetch live news by keyword (NewsAPI)
#   Module 2 — /analyze → AI sentiment + wellness analysis
#
# To start the server:
#   cd Backend
#   python -m uvicorn app.main:app --reload
#
# Then visit:
#   http://127.0.0.1:8000/       → Health check
#   http://127.0.0.1:8000/docs   → Interactive Swagger UI (all endpoints)
#   http://127.0.0.1:8000/news?keyword=AI        → Module 1
#   POST http://127.0.0.1:8000/analyze           → Module 2
# =============================================================

from fastapi import FastAPI

# Import centralized settings — defined ONCE in config.py
from app.config import APP_TITLE, APP_VERSION, APP_DESCRIPTION

# -----------------------------------------------
# Import routers — each file handles a group of routes
# Adding a new feature = create a new router file + one line here
# -----------------------------------------------
from app.routers import news     # Module 1: /news — Live news fetching
from app.routers import analyze  # Module 2: /analyze — AI analysis engine


# -----------------------------------------------
# Create the FastAPI application instance
#
# This is the main "engine". FastAPI uses the title, version,
# and description to auto-generate the /docs Swagger UI.
# -----------------------------------------------
app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    contact={
        "name": "Gurnoor — AI News Authenticity & Mental Wellness Analyzer",
    },
    license_info={
        "name": "MIT",
    },
)


# -----------------------------------------------
# Register Routers
#
# app.include_router() plugs each router into the main app.
# All routes in news.py start with /news (defined via prefix).
# All routes in analyze.py start with /analyze (defined via prefix).
#
# Future modules:
#   from app.routers import authenticity
#   app.include_router(authenticity.router)
# -----------------------------------------------
app.include_router(news.router)     # Registers: GET /news
app.include_router(analyze.router)  # Registers: POST /analyze


# -----------------------------------------------
# Root Route — Server Health Check
#
# GET /
# This is a simple check to confirm the server is live.
# In production, uptime monitors ping this to check health.
# -----------------------------------------------
@app.get("/", tags=["Health"])
def root():
    """
    ## Server Health Check

    Returns a welcome message and links to available API endpoints.

    **Modules available:**
    - `GET /news?keyword=<topic>` — Module 1: Fetch live news
    - `POST /analyze` — Module 2: AI sentiment & wellness analysis
    - `GET /docs` — Interactive Swagger documentation
    """
    return {
        "status":   "online",
        "message":  "AI News Authenticity & Mental Wellness Analyzer — API is running.",
        "version":  APP_VERSION,
        "modules": {
            "module_1": "GET  /news?keyword=<topic>  — Live news fetching",
            "module_2": "POST /analyze               — AI sentiment & wellness analysis",
        },
        "docs": "Visit /docs for the full interactive API documentation",
    }
