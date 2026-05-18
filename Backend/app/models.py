# =============================================================
# app/models.py — SQLAlchemy ORM Table Definition (v2)
#
# WHAT CHANGED IN v2:
#   Added two new nullable columns:
#     - quick_summary       : stores the AI-generated or extractive summary
#     - reading_time_label  : stores "about 1 minute" style label
#
# SAFE MIGRATION STRATEGY:
#   SQLAlchemy's create_all() is idempotent — it never drops existing tables.
#   The new columns are nullable=True so existing rows are unaffected.
#   A safe ALTER TABLE migration runs in main.py's startup event to add
#   the columns to any existing database without deleting old data.
# =============================================================

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

from app.database import Base


class AnalysisRecord(Base):
    """
    ORM model for the 'analysis_history' database table.

    Maps to:
        Table: analysis_history
        Columns: id, keyword, title, source, sentiment, confidence,
                 fear_score, clickbait_score, wellness_impact,
                 emotional_label, quick_summary, reading_time_label,
                 analyzed_at
    """

    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True)

    # Search keyword used to find this article
    keyword = Column(String, nullable=True)

    # Article headline
    title = Column(String, nullable=False)

    # News source name (e.g. "BBC News")
    source = Column(String, nullable=True)

    # AI sentiment result: "POSITIVE", "NEGATIVE", or "NEUTRAL"
    sentiment = Column(String, nullable=False)

    # HuggingFace model confidence (0.0–1.0)
    confidence = Column(Float, nullable=False)

    # Fear keyword density score (0.0–1.0)
    fear_score = Column(Float, nullable=False)

    # Clickbait pattern score (0.0–1.0)
    clickbait_score = Column(Float, nullable=False)

    # Wellness impact level: "LOW", "MODERATE", or "HIGH"
    wellness_impact = Column(String, nullable=False)

    # Human-friendly emotional label
    emotional_label = Column(String, nullable=True)

    # AI-generated or extractive article summary (NEW in v2)
    quick_summary = Column(String, nullable=True)

    # Human-readable reading time label (NEW in v2)
    reading_time_label = Column(String, nullable=True)

    # Auto-filled timestamp at insert time
    analyzed_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AnalysisRecord id={self.id} "
            f"sentiment={self.sentiment!r} "
            f"title={self.title[:40]!r}>"
        )
