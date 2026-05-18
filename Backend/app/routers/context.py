# =============================================================
# app/routers/context.py — GET /context Endpoint  (Module 4)
#
# This is a thin router — all heavy logic lives in context_service.py.
# This file's only job:
#   1. Define the route URL and query parameters
#   2. Validate the incoming `topic` string
#   3. Call the service and return the result
#
# ENDPOINT:
#   GET /context?topic=<news headline or keyword>
#
# EXAMPLE CALLS:
#   http://127.0.0.1:8000/context?topic=gold+prices
#   http://127.0.0.1:8000/context?topic=artificial+intelligence
#   http://127.0.0.1:8000/context?topic=climate+change+2024
#
# DESIGN PATTERN:
#   Mirrors the existing news.py and history.py routers exactly —
#   same error handling style, same logging, same response pattern.
# =============================================================

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.context import ContextResponse
from app.services.context_service import get_context

logger = logging.getLogger(__name__)


# -----------------------------------------------
# Create the router — all routes here start with /context
# -----------------------------------------------
router = APIRouter(
    prefix="/context",
    tags=["Historical Context"],  # Groups this route under its own section in /docs
)


# =============================================================
# GET /context?topic=<string>
#
# Query Parameters:
#   topic (required) — The news headline or keyword to fetch context for.
#                      Min 3 chars, max 200 chars.
#
# Returns: ContextResponse (see schemas/context.py)
#
# Error responses:
#   422 — topic too short / too long (FastAPI validation)
#   500 — unexpected server error in the service layer
# =============================================================
@router.get(
    "/",
    response_model=ContextResponse,
    summary="Get Historical Context for a Topic",
)
def get_historical_context(
    topic: str = Query(
        ...,                   # Required — no default value
        min_length=3,
        max_length=200,
        description=(
            "The news headline or keyword to look up historical context for. "
            "Example: 'gold prices', 'artificial intelligence', 'bitcoin crash'"
        ),
        examples=["gold prices rise globally"],
    ),
):
    """
    ## Historical Context & News Background  (Module 4)

    Fetches **factual** historical background for any news topic using:
    - **Wikipedia REST API** — editor-reviewed summaries, timeline, significance
    - **NewsAPI** — real published articles as reference sources

    > ⚠️ **No hallucinations.** Every piece of text in the response originates
    > from Wikipedia or an actual published news article. If Wikipedia has no
    > matching page, graceful empty fields are returned instead of invented content.

    **Returns:**
    - `historical_context` — Wikipedia introductory summary
    - `timeline_points`    — Chronological key dates extracted from Wikipedia
    - `key_events`         — Important factual sentences from the Wikipedia extract
    - `why_it_matters`     — Broader significance paragraph (Wikipedia-sourced)
    - `related_topics`     — Subject areas linked to this topic
    - `sources`            — Real published articles from NewsAPI (with URLs)
    - `wikipedia_url`      — Direct link to the Wikipedia source page

    **Example:**
    ```
    GET /context?topic=gold+prices
    ```
    """

    # -----------------------------------------------
    # Call the service layer — this does all the work.
    # The router's only job is routing + validation.
    # -----------------------------------------------
    try:
        logger.info("Historical context request | topic=%r", topic)
        result = get_context(topic)
        logger.info("Historical context success  | topic=%r", topic)
        return result

    except Exception as exc:
        # Log the full error for debugging, but return a clean message to the user
        logger.exception("Unexpected error in context service for topic=%r: %s", topic, exc)
        raise HTTPException(
            status_code=500,
            detail=(
                f"An unexpected error occurred while fetching historical context "
                f"for \"{topic}\". Please try again. "
                f"(Internal: {type(exc).__name__})"
            ),
        )
