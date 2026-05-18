# =============================================================
# app/routers/history.py — GET /history + DELETE /history/{id}
#
# WHAT CHANGED IN v2:
#   - Added filter params: sentiment, search, impact, sort
#   - Added DELETE /history/{record_id} endpoint
#   - Added GET /history/analytics endpoint for dashboard data
# =============================================================

import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/history",
    tags=["History"],
)


# =============================================================
# GET /history — Paginated + Filtered History
# =============================================================

@router.get("/")
def get_history(
    limit: int = Query(default=50, ge=1, le=200, description="Records per page (1–200)."),
    offset: int = Query(default=0, ge=0, description="Skip N records."),
    sentiment: Optional[str] = Query(
        default=None,
        description="Filter by sentiment: POSITIVE, NEGATIVE, NEUTRAL"
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=200,
        description="Search by keyword or title text (case-insensitive)."
    ),
    impact: Optional[str] = Query(
        default=None,
        description="Filter by wellness impact: LOW, MODERATE, HIGH"
    ),
    sort: str = Query(
        default="newest",
        description="Sort order: 'newest' or 'oldest'"
    ),
    db: Session = Depends(get_db),
):
    """
    ## Analysis History

    Returns filtered + paginated analysis records from the SQLite database.

    **Filters:**
    - `sentiment` — POSITIVE / NEGATIVE / NEUTRAL
    - `search` — case-insensitive keyword/title search
    - `impact` — LOW / MODERATE / HIGH
    - `sort` — newest (default) or oldest
    """

    sort_desc = (sort.lower() != "oldest")

    records = crud.get_analysis_history_filtered(
        db,
        sentiment=sentiment,
        keyword=search,
        impact=impact,
        sort_desc=sort_desc,
        limit=limit,
        offset=offset,
    )
    total = crud.count_analysis_records_filtered(
        db, sentiment=sentiment, keyword=search, impact=impact
    )

    records_list = [
        {
            "id":                 r.id,
            "keyword":            r.keyword,
            "title":              r.title,
            "source":             r.source,
            "sentiment":          r.sentiment,
            "confidence":         r.confidence,
            "fear_score":         r.fear_score,
            "clickbait_score":    r.clickbait_score,
            "wellness_impact":    r.wellness_impact,
            "emotional_label":    r.emotional_label,
            "quick_summary":      r.quick_summary,
            "reading_time_label": r.reading_time_label,
            "analyzed_at":        r.analyzed_at.isoformat() if r.analyzed_at else None,
        }
        for r in records
    ]

    return {
        "total_records": total,
        "limit":         limit,
        "offset":        offset,
        "records":       records_list,
    }


# =============================================================
# GET /history/analytics — Dashboard aggregates
# =============================================================

@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """
    ## Dashboard Analytics

    Returns aggregated statistics for the analytics dashboard:
    - Sentiment distribution counts
    - Wellness impact distribution
    - Top searched keywords
    - Top analyzed news sources
    - Daily analysis activity (last 14 days)
    - Highest fear-scored topics
    - Total record count
    """
    total             = crud.count_analysis_records(db)
    sentiment_counts  = crud.get_sentiment_counts(db)
    impact_counts     = crud.get_wellness_impact_counts(db)
    top_keywords      = crud.get_top_keywords(db, limit=10)
    top_sources       = crud.get_top_sources(db, limit=10)
    daily_activity    = crud.get_daily_activity(db, days=14)
    high_fear_topics  = crud.get_high_fear_topics(db, limit=5)

    return {
        "total_analyses":    total,
        "sentiment_counts":  sentiment_counts,
        "impact_counts":     impact_counts,
        "top_keywords":      top_keywords,
        "top_sources":       top_sources,
        "daily_activity":    daily_activity,
        "high_fear_topics":  high_fear_topics,
    }


# =============================================================
# DELETE /history/{record_id}
# =============================================================

@router.delete("/{record_id}")
def delete_history_record(
    record_id: int,
    db: Session = Depends(get_db),
):
    """
    ## Delete a History Record

    Permanently removes a single analysis record from the database.

    **Path parameter:** `record_id` — the integer ID of the record to delete.

    Returns 404 if the record does not exist.
    """
    deleted = crud.delete_analysis_record(db, record_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found.")
    return {"deleted": True, "id": record_id}
