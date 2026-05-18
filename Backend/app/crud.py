# =============================================================
# app/crud.py — CRUD Helper Functions (v2)
#
# WHAT CHANGED IN v2:
#   - create_analysis_record: accepts quick_summary, reading_time_label
#   - delete_analysis_record: deletes a single record by ID
#   - get_analysis_history_filtered: filter by sentiment / keyword
# =============================================================

import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models import AnalysisRecord

logger = logging.getLogger(__name__)


# =============================================================
# CREATE — Save one analysis result
# =============================================================

def create_analysis_record(
    db: Session,
    *,
    keyword:            str | None,
    title:              str,
    source:             str | None,
    sentiment:          str,
    confidence:         float,
    fear_score:         float,
    clickbait_score:    float,
    wellness_impact:    str,
    emotional_label:    str | None,
    quick_summary:      str | None = None,
    reading_time_label: str | None = None,
) -> AnalysisRecord:
    """
    Insert one new row into the analysis_history table.

    All parameters are keyword-only (enforced by the bare * after db).
    quick_summary and reading_time_label are new in v2 — both optional.
    """
    record = AnalysisRecord(
        keyword             = keyword,
        title               = title,
        source              = source,
        sentiment           = sentiment,
        confidence          = round(confidence, 4),
        fear_score          = round(fear_score, 4),
        clickbait_score     = round(clickbait_score, 4),
        wellness_impact     = wellness_impact,
        emotional_label     = emotional_label,
        quick_summary       = quick_summary,
        reading_time_label  = reading_time_label,
    )

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# =============================================================
# READ — Retrieve history (basic)
# =============================================================

def get_analysis_history(
    db:     Session,
    *,
    limit:  int = 50,
    offset: int = 0,
) -> list[AnalysisRecord]:
    """
    Return the most recent analysis records, newest first.
    """
    return (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.analyzed_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


# =============================================================
# READ — Filtered history
# =============================================================

def get_analysis_history_filtered(
    db:        Session,
    *,
    sentiment: str | None = None,
    keyword:   str | None = None,
    impact:    str | None = None,
    sort_desc: bool = True,
    limit:     int = 100,
    offset:    int = 0,
) -> list[AnalysisRecord]:
    """
    Return filtered analysis records.

    Parameters
    ----------
    sentiment : str | None
        Filter by exact sentiment label: "POSITIVE", "NEGATIVE", "NEUTRAL".
    keyword : str | None
        Filter by keyword (case-insensitive contains search on both
        the keyword column and the title column).
    impact : str | None
        Filter by wellness impact: "LOW", "MODERATE", "HIGH".
    sort_desc : bool
        True = newest first (default), False = oldest first.
    limit : int
        Max records to return.
    offset : int
        Skip N records (pagination).
    """
    q = db.query(AnalysisRecord)

    if sentiment:
        q = q.filter(AnalysisRecord.sentiment == sentiment.upper())

    if keyword:
        term = f"%{keyword.lower()}%"
        q = q.filter(
            or_(
                AnalysisRecord.keyword.ilike(term),
                AnalysisRecord.title.ilike(term),
            )
        )

    if impact:
        q = q.filter(AnalysisRecord.wellness_impact == impact.upper())

    if sort_desc:
        q = q.order_by(AnalysisRecord.analyzed_at.desc())
    else:
        q = q.order_by(AnalysisRecord.analyzed_at.asc())

    return q.offset(offset).limit(limit).all()


# =============================================================
# READ — Count records
# =============================================================

def count_analysis_records(db: Session) -> int:
    """Return total number of rows in analysis_history."""
    return db.query(AnalysisRecord).count()


def count_analysis_records_filtered(
    db:        Session,
    *,
    sentiment: str | None = None,
    keyword:   str | None = None,
    impact:    str | None = None,
) -> int:
    """Return count after applying the same filters as get_analysis_history_filtered."""
    q = db.query(AnalysisRecord)

    if sentiment:
        q = q.filter(AnalysisRecord.sentiment == sentiment.upper())

    if keyword:
        term = f"%{keyword.lower()}%"
        q = q.filter(
            or_(
                AnalysisRecord.keyword.ilike(term),
                AnalysisRecord.title.ilike(term),
            )
        )

    if impact:
        q = q.filter(AnalysisRecord.wellness_impact == impact.upper())

    return q.count()


# =============================================================
# READ — Analytics aggregates (for dashboard)
# =============================================================

def get_sentiment_counts(db: Session) -> dict:
    """
    Return counts of each sentiment label in the history table.
    Example: {"POSITIVE": 12, "NEGATIVE": 30, "NEUTRAL": 8}
    """
    from sqlalchemy import func
    rows = (
        db.query(AnalysisRecord.sentiment, func.count(AnalysisRecord.id))
        .group_by(AnalysisRecord.sentiment)
        .all()
    )
    return {label: count for label, count in rows}


def get_wellness_impact_counts(db: Session) -> dict:
    """
    Return counts of each wellness impact level.
    Example: {"LOW": 20, "MODERATE": 18, "HIGH": 12}
    """
    from sqlalchemy import func
    rows = (
        db.query(AnalysisRecord.wellness_impact, func.count(AnalysisRecord.id))
        .group_by(AnalysisRecord.wellness_impact)
        .all()
    )
    return {level: count for level, count in rows}


def get_top_keywords(db: Session, limit: int = 10) -> list[dict]:
    """
    Return the most frequently searched keywords.
    Returns list of {"keyword": str, "count": int}.
    """
    from sqlalchemy import func
    rows = (
        db.query(AnalysisRecord.keyword, func.count(AnalysisRecord.id).label("count"))
        .filter(AnalysisRecord.keyword.isnot(None))
        .filter(AnalysisRecord.keyword != "")
        .group_by(AnalysisRecord.keyword)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(limit)
        .all()
    )
    return [{"keyword": kw, "count": cnt} for kw, cnt in rows]


def get_top_sources(db: Session, limit: int = 10) -> list[dict]:
    """
    Return most frequently analyzed news sources.
    Returns list of {"source": str, "count": int}.
    """
    from sqlalchemy import func
    rows = (
        db.query(AnalysisRecord.source, func.count(AnalysisRecord.id).label("count"))
        .filter(AnalysisRecord.source.isnot(None))
        .filter(AnalysisRecord.source != "")
        .group_by(AnalysisRecord.source)
        .order_by(func.count(AnalysisRecord.id).desc())
        .limit(limit)
        .all()
    )
    return [{"source": src, "count": cnt} for src, cnt in rows]


def get_daily_activity(db: Session, days: int = 14) -> list[dict]:
    """
    Return analysis count per day for the last N days.
    Returns list of {"date": "YYYY-MM-DD", "count": int}.
    """
    from sqlalchemy import func
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            func.date(AnalysisRecord.analyzed_at).label("date"),
            func.count(AnalysisRecord.id).label("count"),
        )
        .filter(AnalysisRecord.analyzed_at >= since)
        .group_by(func.date(AnalysisRecord.analyzed_at))
        .order_by(func.date(AnalysisRecord.analyzed_at).asc())
        .all()
    )
    return [{"date": str(row.date), "count": row.count} for row in rows]


def get_high_fear_topics(db: Session, limit: int = 5) -> list[dict]:
    """
    Return the highest fear-scored articles.
    """
    rows = (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.fear_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "title":      r.title[:70],
            "fear_score": r.fear_score,
            "keyword":    r.keyword or "—",
            "sentiment":  r.sentiment,
        }
        for r in rows
    ]


# =============================================================
# DELETE — Remove a single record
# =============================================================

def delete_analysis_record(db: Session, record_id: int) -> bool:
    """
    Delete a single analysis record by its ID.

    Returns True if the record was found and deleted,
    False if no record with that ID exists.
    """
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()

    if record is None:
        logger.warning("Delete: record ID=%d not found.", record_id)
        return False

    db.delete(record)
    db.commit()
    logger.info("✅ Deleted analysis record ID=%d", record_id)
    return True
