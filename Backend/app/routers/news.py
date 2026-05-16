# =============================================================
# app/routers/news.py — The /news route
#
# This file handles everything related to fetching live news.
# When a user visits /news?keyword=AI, this function runs.
#
# Flow:
#   Browser/Frontend  →  FastAPI  →  This file  →  NewsAPI  →  Back to user
# =============================================================

import requests                    # Used to make HTTP GET calls to NewsAPI

from fastapi import APIRouter, HTTPException, Query

# Import our centralized config values (API key, URL, settings)
# Instead of hard-coding values here, we read them from config.py
from app.config import (
    NEWSAPI_KEY,
    NEWSAPI_BASE_URL,
    NEWSAPI_LANGUAGE,
    NEWSAPI_PAGE_SIZE,
)

# -----------------------------------------------
# Create a router — think of it as a mini-app
# that handles only the /news routes.
# All URLs here will be prefixed with /news
# -----------------------------------------------
router = APIRouter(
    prefix="/news",   # All routes in this file start with /news
    tags=["News"],    # Groups these routes under "News" in /docs
)


# =============================================================
# GET /news?keyword=<your_keyword>
#
# Example calls:
#   http://127.0.0.1:8000/news?keyword=AI
#   http://127.0.0.1:8000/news?keyword=climate+change
#
# Query Parameters:
#   keyword (required) — The topic you want news about
#   page_size (optional) — How many articles to return (1–50, default: 10)
# =============================================================
@router.get("/")
def get_news(
    keyword: str = Query(
        ...,           # '...' means this parameter is REQUIRED — no default
        description="The keyword to search news for. Example: 'AI', 'Bitcoin', 'Climate'",
        min_length=2,  # Keyword must be at least 2 characters
        max_length=100,
    ),
    page_size: int = Query(
        default=NEWSAPI_PAGE_SIZE,  # Default comes from config.py (10)
        ge=1,                       # Must be >= 1
        le=50,                      # Must be <= 50
        description="Number of articles to return (1–50). Defaults to 10.",
    ),
):
    """
    ## Fetch Live News Headlines

    Fetches real-time news articles for a given keyword using [NewsAPI](https://newsapi.org).

    **How to use:**
    - `GET /news?keyword=AI` — Returns latest 10 AI articles
    - `GET /news?keyword=Bitcoin&page_size=5` — Returns 5 Bitcoin articles

    **Returns:** keyword, total results, article count, and a list of articles with
    title, description, source, URL, and publication date.
    """

    # -----------------------------------------------
    # Step 1: Validate that the API key exists
    # The key is loaded from config.py which reads the .env file.
    # If the key is missing, there's no point calling NewsAPI.
    # -----------------------------------------------
    if not NEWSAPI_KEY:
        # HTTP 500 = Internal Server Error (our configuration problem, not the user's fault)
        raise HTTPException(
            status_code=500,
            detail=(
                "Server configuration error: NEWSAPI_KEY is not set. "
                "Please add NEWSAPI_KEY=your_key_here to your .env file."
            ),
        )

    # -----------------------------------------------
    # Step 2: Build the query parameters for NewsAPI
    #
    # When you call: requests.get(url, params=params)
    # The 'params' dict gets appended to the URL like this:
    #   https://newsapi.org/v2/everything?q=AI&language=en&sortBy=publishedAt&...
    # -----------------------------------------------
    params = {
        "q":        keyword,           # The search keyword from the user
        "language": NEWSAPI_LANGUAGE,  # "en" — only English articles (from config.py)
        "sortBy":   "publishedAt",     # Sort by newest first
        "pageSize": page_size,         # Number of results (from query param or default)
        "apiKey":   NEWSAPI_KEY,       # Your secret API key (from config.py / .env)
    }

    # -----------------------------------------------
    # Step 3: Call the NewsAPI using requests.get()
    #
    # requests.get(url, params=params, timeout=10) does:
    #   1. Builds the full URL with params appended
    #   2. Sends an HTTP GET request to that URL
    #   3. Waits up to 10 seconds for a response
    #   4. Returns a Response object with .status_code and .json()
    # -----------------------------------------------
    try:
        response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=10)

        # raise_for_status() checks if the HTTP status code is 4xx or 5xx.
        # If it is, it throws an HTTPError exception immediately.
        response.raise_for_status()

    except requests.exceptions.ConnectionError:
        # This happens when there's no internet or NewsAPI is unreachable
        raise HTTPException(
            status_code=503,
            detail="Cannot reach NewsAPI. Please check your internet connection.",
        )
    except requests.exceptions.Timeout:
        # This happens when NewsAPI takes longer than 10 seconds to respond
        raise HTTPException(
            status_code=504,
            detail="NewsAPI took too long to respond. Please try again.",
        )
    except requests.exceptions.HTTPError as e:
        # This happens when NewsAPI returns a 4xx or 5xx HTTP status code
        raise HTTPException(
            status_code=response.status_code,
            detail=f"NewsAPI HTTP error: {str(e)}",
        )
    except requests.exceptions.RequestException as e:
        # Catch-all for any other requests-related errors
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while calling NewsAPI: {str(e)}",
        )

    # -----------------------------------------------
    # Step 4: Parse the JSON response from NewsAPI
    #
    # response.json() converts the raw API response text
    # into a Python dictionary we can work with.
    # NewsAPI returns a structure like:
    #   {
    #     "status": "ok",
    #     "totalResults": 123,
    #     "articles": [ { "title": "...", "description": "...", ... }, ... ]
    #   }
    # -----------------------------------------------
    data = response.json()

    # NewsAPI sometimes returns status "error" even with HTTP 200
    if data.get("status") != "ok":
        raise HTTPException(
            status_code=400,
            detail=f"NewsAPI returned an error: {data.get('message', 'Unknown error')}",
        )

    # -----------------------------------------------
    # Step 5: Extract only the fields we need
    #
    # NewsAPI returns many fields per article (author, urlToImage, content, etc.)
    # We only pick the 5 fields relevant to our app.
    # -----------------------------------------------
    articles = []

    for article in data.get("articles", []):
        # article.get("source", {}).get("name") safely reads nested dict values
        # If "source" key is missing, {} is used as default so .get("name") won't crash

        articles.append({
            "title":        article.get("title"),         # Headline of the article
            "description":  article.get("description"),   # Short summary
            "source":       article.get("source", {}).get("name"),  # e.g. "BBC News"
            "url":          article.get("url"),            # Link to full article
            "published_at": article.get("publishedAt"),   # ISO 8601 timestamp
        })

    # -----------------------------------------------
    # Step 6: Return a clean, structured JSON response
    #
    # FastAPI automatically converts this Python dict into JSON.
    # The frontend will receive this as a JSON object.
    # -----------------------------------------------
    return {
        "keyword":        keyword,                      # Echo back the search term
        "total_results":  data.get("totalResults", 0),  # Total matches found by NewsAPI
        "articles_shown": len(articles),                # How many we're returning
        "articles":       articles,                     # The actual list of articles
    }
