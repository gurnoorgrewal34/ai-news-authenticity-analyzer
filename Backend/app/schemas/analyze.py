# =============================================================
# app/schemas/analyze.py — Request & Response Models (v2)
#
# WHAT CHANGED IN v2:
#   - Added AIFlags nested schema (fake_news_risk, emotional_framing)
#   - Added ai_flags field to AnalyzeResponse
# =============================================================

from pydantic import BaseModel, Field
from typing import Optional, List


# =============================================================
# REQUEST SCHEMA
# =============================================================

class AnalyzeRequest(BaseModel):
    """Input data for POST /analyze."""

    title: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The headline or title of the news article.",
        examples=["Scientists discover AI can predict dementia 10 years early"],
    )

    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="The article's summary or description text.",
        examples=["Researchers at MIT have found that speech patterns can reveal..."],
    )

    keyword: Optional[str] = Field(
        default=None,
        max_length=100,
        description="The search keyword used to find this article.",
        examples=["gold prices"],
    )

    source: Optional[str] = Field(
        default=None,
        max_length=200,
        description="The news source name (e.g. 'BBC News', 'Reuters').",
        examples=["BBC News"],
    )


# =============================================================
# NESTED RESPONSE SCHEMAS
# =============================================================

class SentimentResult(BaseModel):
    """Raw sentiment result from the HuggingFace model."""
    label: str               # "POSITIVE", "NEGATIVE", or "NEUTRAL"
    confidence: float        # 0.0 to 1.0
    confidence_percent: str  # e.g. "87.3%"


class WellnessScores(BaseModel):
    """Custom wellness scoring metrics."""
    fear_score: float       # 0.0–1.0
    clickbait_score: float  # 0.0–1.0
    wellness_impact: str    # "LOW", "MODERATE", or "HIGH"
    wellness_message: str   # Human-readable explanation


class AnalysisSummary(BaseModel):
    """High-level summary of the full analysis."""
    overall_tone: str         # "Positive", "Negative", or "Neutral"
    emotional_intensity: str  # "Low", "Moderate", or "High"
    recommendation: str       # Practical advice for the reader


class ArticleInsights(BaseModel):
    """AI-generated content intelligence."""
    quick_summary: str           # 2–3 sentence summary
    key_points: List[str]        # 3–5 extracted bullet points
    reading_time_seconds: int    # Estimated reading time in seconds
    reading_time_label: str      # e.g. "about 1 minute"
    emotional_label: str         # e.g. "😊 Uplifting & Positive"
    emotional_description: str   # One-sentence explanation
    summarizer_used: bool        # True = AI model, False = fallback


class AIFlags(BaseModel):
    """
    New AI-derived risk flags for the article.

    fake_news_risk:
        Estimated risk that this article uses fake-news tactics.
        Based on: sensational words + emotional language + clickbait patterns.
        Values: "LOW" | "MEDIUM" | "HIGH"

    emotional_framing:
        The primary emotional framing style detected in the article.
        Values: "Neutral" | "Fear-driven" | "Emotionally Charged" | "Sensationalized"

    fake_news_risk_reason:
        A short explanation of why the risk level was assigned.
    """
    fake_news_risk:        str = Field(description="LOW | MEDIUM | HIGH fake news risk indicator.")
    emotional_framing:     str = Field(description="Detected emotional framing style.")
    fake_news_risk_reason: str = Field(description="Brief explanation of the risk assessment.")


# =============================================================
# MAIN RESPONSE SCHEMA
# =============================================================

class AnalyzeResponse(BaseModel):
    """Full analysis result returned by POST /analyze."""

    # Echo back what was analyzed
    title: str
    description_preview: str

    # AI model output
    sentiment: SentimentResult

    # Custom wellness scoring
    wellness_scores: WellnessScores

    # Human-readable summary
    summary: AnalysisSummary

    # AI-generated content intelligence
    article_insights: ArticleInsights

    # New in v2: AI risk flags
    ai_flags: AIFlags

    # Metadata
    model_used: str
    analysis_version: str
