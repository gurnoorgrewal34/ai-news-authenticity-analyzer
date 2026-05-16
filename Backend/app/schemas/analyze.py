# =============================================================
# app/schemas/analyze.py — Request & Response Data Models
#
# WHY SCHEMAS EXIST:
#   FastAPI uses Pydantic models (called "schemas") to:
#     1. Validate incoming request data automatically
#     2. Document the API shape in Swagger /docs
#     3. Provide type safety throughout the codebase
#
# DIFFERENCE FROM ROUTERS:
#   - Routers = WHERE the request goes (URL → function)
#   - Schemas = WHAT shape the data must be in
# =============================================================

from pydantic import BaseModel, Field
from typing import Optional


# =============================================================
# REQUEST SCHEMA — What the user sends to POST /analyze
#
# The client sends a JSON body like:
#   {
#     "title": "Scientists discover new AI breakthrough",
#     "description": "Researchers at MIT have found..."
#   }
# =============================================================
class AnalyzeRequest(BaseModel):
    """
    Input data for the AI analysis endpoint.
    Both fields are required. FastAPI validates types automatically.
    """

    title: str = Field(
        ...,                          # Required — no default
        min_length=3,                 # Must be at least 3 characters
        max_length=500,               # Reasonable title length limit
        description="The headline or title of the news article.",
        examples=["Scientists discover AI can predict dementia 10 years early"],
    )

    description: str = Field(
        ...,                          # Required
        min_length=10,                # Must be at least 10 characters
        max_length=5000,              # Article descriptions can be long
        description="The article's summary or description text.",
        examples=["Researchers at MIT have found that speech patterns can reveal..."],
    )


# =============================================================
# NESTED SCHEMAS — Sub-objects inside the response
# =============================================================

class SentimentResult(BaseModel):
    """The raw sentiment result from the HuggingFace model."""
    label: str             # "POSITIVE", "NEGATIVE", or "NEUTRAL"
    confidence: float      # 0.0 to 1.0 — how sure the model is
    confidence_percent: str  # Human-readable, e.g. "87.3%"


class WellnessScores(BaseModel):
    """Custom scoring metrics we compute on top of the AI output."""
    fear_score: float          # 0.0 to 1.0 — how fear-inducing the text is
    clickbait_score: float     # 0.0 to 1.0 — how exaggerated/clickbait-y it is
    wellness_impact: str       # "LOW", "MODERATE", or "HIGH" impact on mental health
    wellness_message: str      # A human-readable explanation for the user


class AnalysisSummary(BaseModel):
    """High-level summary of the full analysis."""
    overall_tone: str          # "Positive", "Negative", or "Neutral"
    emotional_intensity: str   # "Low", "Moderate", or "High"
    recommendation: str        # Practical advice for the reader


# =============================================================
# RESPONSE SCHEMA — What we send back to the client
#
# FastAPI uses this to:
#   1. Validate our own output (catches bugs in our code)
#   2. Auto-generate the response schema in /docs
# =============================================================
class AnalyzeResponse(BaseModel):
    """
    Full analysis result returned by POST /analyze.
    """

    # Echo back what was analyzed (for frontend display)
    title: str
    description_preview: str   # First 100 characters of the description

    # AI model output
    sentiment: SentimentResult

    # Our custom scoring
    wellness_scores: WellnessScores

    # Human-readable summary
    summary: AnalysisSummary

    # Metadata
    model_used: str            # Which HuggingFace model was used
    analysis_version: str      # For tracking purposes
