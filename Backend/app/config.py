# =============================================================
# app/config.py — Central Configuration File
#
# WHY THIS FILE EXISTS:
#   Instead of copy-pasting settings (like the API key or URL)
#   all over the project, we define them ONCE here.
#   Every other file imports from here.
#
# HOW ENVIRONMENT VARIABLES WORK:
#   1. You store secrets in a file called ".env"  (e.g. NEWSAPI_KEY=abc123)
#   2. load_dotenv() reads that file and loads each key=value
#      into the system's environment variables (like a temporary memory)
#   3. os.getenv("NEWSAPI_KEY") then retrieves that value safely
#   4. The .env file is NEVER pushed to GitHub — it stays private
# =============================================================

import os                        # Built-in module to access environment variables
from dotenv import load_dotenv   # Reads the .env file and loads it into the environment

# -----------------------------------------------
# Load the .env file
# This must be called BEFORE any os.getenv() calls.
# dotenv searches for .env in the current directory and parent directories.
# -----------------------------------------------
load_dotenv()


# =============================================================
# App Metadata
# Used in main.py to label the FastAPI application
# =============================================================
APP_TITLE       = "AI News Authenticity & Mental Wellness Analyzer"
APP_VERSION     = "1.0.0"
APP_DESCRIPTION = (
    "A professional-grade backend API that fetches live news, "
    "analyzes sentiment using HuggingFace AI, and assesses mental wellness impact.\n\n"
    "**Module 1** — `GET /news` — Fetch live headlines by keyword via NewsAPI.\n\n"
    "**Module 2** — `POST /analyze` — AI sentiment analysis, fear scoring, "
    "clickbait detection, and mental wellness impact assessment."
)


# =============================================================
# NewsAPI Configuration
#
# NEWSAPI_KEY:
#   - Loaded securely from your .env file
#   - os.getenv("NEWSAPI_KEY", "") returns "" if the key isn't set
#     (the empty string "" is the safe fallback — we check for it in news.py)
#
# NEWSAPI_BASE_URL:
#   - The endpoint we call to search for news articles
#   - /v2/everything → searches all articles across all sources
#   - Alternative: /v2/top-headlines → only top headlines
#
# NEWSAPI_LANGUAGE:
#   - Filters results to only English articles
#   - Other options: "fr" (French), "de" (German), "es" (Spanish), etc.
#
# NEWSAPI_PAGE_SIZE:
#   - Default number of articles to return per request
#   - Free NewsAPI plan supports up to 100 per request
# =============================================================
NEWSAPI_KEY       = os.getenv("NEWSAPI_KEY", "")         # Your secret API key from .env
NEWSAPI_BASE_URL  = "https://newsapi.org/v2/everything"  # NewsAPI search endpoint
NEWSAPI_LANGUAGE  = "en"                                  # Return English articles only
NEWSAPI_PAGE_SIZE = 10                                    # Default: return 10 articles
