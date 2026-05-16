# =============================================================
# app/routers/analyze.py — Module 2: AI News Analysis Engine
#
# This file handles the POST /analyze endpoint.
# It takes a news title + description and returns:
#   - Sentiment (positive/negative/neutral) via HuggingFace AI
#   - Confidence score (how certain the model is)
#   - Fear score (custom logic)
#   - Clickbait score (custom keyword detection)
#   - Mental wellness impact level + recommendation
#
# =============================================================
# HOW HUGGINGFACE TRANSFORMERS PIPELINE WORKS:
#
#   A "pipeline" is a high-level wrapper that does three things:
#     1. TOKENIZE  — converts text into numbers the model understands
#     2. INFERENCE — runs the model to produce predictions
#     3. DECODE    — converts the model's output back to human-readable labels
#
#   You don't need to know the math. You just call:
#     pipeline("sentiment-analysis")("Your text here")
#   And it returns: [{"label": "POSITIVE", "score": 0.92}]
#
# HOW NLP INFERENCE WORKS:
#   - The model has already been TRAINED on millions of examples.
#   - "Inference" just means: "run this trained model on new input."
#   - No learning happens here — the model's weights are fixed.
#   - It's like asking an expert to read a sentence (they already know the language).
#
# TRAINING vs INFERENCE:
#   Training  = Teaching the model (takes days, costs $$$, done by HuggingFace)
#   Inference = Using the trained model (takes milliseconds, done by us)
#
# WHY PRETRAINED MODELS ARE USEFUL:
#   - Trained on billions of words from the internet
#   - They already understand grammar, context, and emotion
#   - We benefit from all that learning for FREE
#   - We just download and use them — no GPU required for small models
#
# =============================================================

import re                              # Built-in: regular expressions for text matching
import logging                         # Built-in: for logging errors and info

from fastapi import APIRouter, HTTPException

# Our Pydantic schemas (request/response shapes)
from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse

# -----------------------------------------------
# Set up a logger for this module
# This prints structured messages to the console
# -----------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------
# Create the router for all /analyze routes
# -----------------------------------------------
router = APIRouter(
    prefix="/analyze",   # All routes here start with /analyze
    tags=["Analysis"],   # Groups routes under "Analysis" in /docs
)


# =============================================================
# MODEL LOADING — Load the HuggingFace pipeline ONCE at startup
#
# WHY LOAD ONCE (not inside the function)?
#   - Loading a model takes 2–5 seconds the first time
#   - If we loaded it inside the function, every request would be slow
#   - By loading at module import time, it loads ONCE when the server starts
#   - All subsequent requests reuse the same loaded model (fast!)
#
# MODEL USED: distilbert-base-uncased-finetuned-sst-2-english
#   - "distilbert" = smaller, faster version of BERT (by Google)
#   - "uncased" = treats "Hello" and "hello" the same way
#   - "finetuned-sst-2" = fine-tuned on SST-2 (Stanford Sentiment Treebank)
#   - This model classifies text as POSITIVE or NEGATIVE
#   - Size: ~268MB — downloads automatically on first use
# =============================================================

# Lazy import: we import transformers here so the server still starts
# even if there's an issue with the ML libraries
try:
    from transformers import pipeline as hf_pipeline

    # pipeline() downloads the model if not cached, then loads it into memory
    # "sentiment-analysis" is the task type — HuggingFace knows which model to use
    # model= specifies the exact pretrained model to use
    sentiment_pipeline = hf_pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        # truncation=True: if text is too long, it cuts it to the model's max length
        # max_length=512: this model can process at most 512 tokens at a time
        truncation=True,
        max_length=512,
    )
    MODEL_LOADED = True
    MODEL_NAME   = "distilbert-base-uncased-finetuned-sst-2-english"
    logger.info("✅ Sentiment analysis model loaded successfully.")

except Exception as e:
    # If the model fails to load, we set a flag and handle it gracefully
    sentiment_pipeline = None
    MODEL_LOADED       = False
    MODEL_NAME         = "unavailable"
    logger.error(f"❌ Failed to load sentiment model: {e}")


# =============================================================
# FEAR KEYWORDS — Words commonly associated with fear/anxiety in news
#
# This is a hand-crafted list we use to compute a "fear score".
# In a real production system, you'd use a fine-tuned emotion model.
# For now, this keyword-matching approach is transparent and explainable.
# =============================================================
FEAR_KEYWORDS = [
    "crisis", "disaster", "attack", "war", "threat", "danger", "deadly",
    "collapse", "emergency", "catastrophe", "terror", "explosion", "shooting",
    "outbreak", "epidemic", "pandemic", "death", "killed", "fatal", "severe",
    "alarming", "warning", "devastating", "tragic", "shocking", "horrific",
    "violence", "murder", "accident", "crash", "flood", "earthquake", "fire",
    "bomb", "weapon", "hostage", "corruption", "fraud", "scandal", "arrested",
]

# =============================================================
# CLICKBAIT PATTERNS — Phrases that signal exaggerated headlines
# =============================================================
CLICKBAIT_PATTERNS = [
    r"\byou won't believe\b",
    r"\bshocking\b",
    r"\bmind.?blowing\b",
    r"\bthis is why\b",
    r"\bthe truth about\b",
    r"\bsecret\b",
    r"\bthey don't want you to know\b",
    r"\bwhat happened next\b",
    r"\bbreaking\b",
    r"\bexclusive\b",
    r"\burgent\b",
    r"\bmust.?see\b",
    r"\bviral\b",
    r"\binstantly\b",
    r"\bwow\b",
    r"\b\d+ (ways|things|reasons|facts|tips)\b",  # e.g. "7 reasons why"
]


# =============================================================
# HELPER FUNCTION: Compute Fear Score
#
# Counts how many fear keywords appear in the text,
# then normalizes to a 0.0–1.0 scale.
# =============================================================
def compute_fear_score(text: str) -> float:
    """
    Returns a fear score between 0.0 (no fear) and 1.0 (very fear-inducing).

    Method: count how many fear keywords appear in the lowercased text,
    cap at a maximum, and normalize.
    """
    text_lower = text.lower()  # Normalize to lowercase for matching

    # Count how many fear keywords appear in the text
    fear_count = sum(1 for word in FEAR_KEYWORDS if word in text_lower)

    # Normalize: cap at 5 matches = maximum fear score of 1.0
    # e.g. 0 matches → 0.0, 3 matches → 0.6, 5+ matches → 1.0
    MAX_FEAR_KEYWORDS = 5
    return round(min(fear_count / MAX_FEAR_KEYWORDS, 1.0), 2)


# =============================================================
# HELPER FUNCTION: Compute Clickbait Score
#
# Uses regex patterns to detect clickbait language in the title.
# =============================================================
def compute_clickbait_score(title: str) -> float:
    """
    Returns a clickbait score between 0.0 (genuine) and 1.0 (very clickbait-y).

    Uses regular expressions to detect common clickbait patterns.
    """
    title_lower = title.lower()

    # Count how many clickbait patterns match
    matches = sum(
        1 for pattern in CLICKBAIT_PATTERNS
        if re.search(pattern, title_lower)
    )

    # Normalize: cap at 4 matches = maximum clickbait score of 1.0
    MAX_CLICKBAIT = 4
    return round(min(matches / MAX_CLICKBAIT, 1.0), 2)


# =============================================================
# HELPER FUNCTION: Determine Emotional Intensity
#
# Combines the AI confidence score with the fear score.
# High confidence + high fear = high emotional intensity.
# =============================================================
def get_emotional_intensity(confidence: float, fear_score: float) -> str:
    """
    Returns 'Low', 'Moderate', or 'High' based on combined signals.

    - confidence: how strongly the AI model felt about the sentiment (0–1)
    - fear_score: how many fear keywords were found (0–1)
    """
    # Combined intensity = average of AI confidence and fear score
    combined = (confidence + fear_score) / 2

    if combined >= 0.70:
        return "High"
    elif combined >= 0.40:
        return "Moderate"
    else:
        return "Low"


# =============================================================
# HELPER FUNCTION: Determine Wellness Impact
#
# Produces a wellness_impact level and a friendly message.
# =============================================================
def get_wellness_impact(
    sentiment_label: str,
    fear_score: float,
    clickbait_score: float
) -> tuple[str, str]:
    """
    Returns (impact_level, message) for mental wellness.

    Considers:
      - Is the sentiment negative?
      - Is the fear score high?
      - Is it clickbait-y (likely designed to provoke anxiety)?
    """

    # A high-impact article = negative AND fear-inducing AND possibly clickbait
    is_negative  = sentiment_label == "NEGATIVE"
    is_fearful   = fear_score >= 0.5
    is_clickbait = clickbait_score >= 0.5

    if is_negative and is_fearful:
        level   = "HIGH"
        message = (
            "⚠️ This article contains strong negative and fear-inducing language. "
            "Consider verifying with multiple sources before forming strong opinions. "
            "Limit exposure to highly stressful news for mental well-being."
        )
    elif is_negative or is_fearful or is_clickbait:
        level   = "MODERATE"
        message = (
            "🔔 This article has some negative or emotionally charged language. "
            "Read critically and be mindful of how news consumption affects your mood."
        )
    else:
        level   = "LOW"
        message = (
            "✅ This article appears to have a neutral or positive tone. "
            "It is likely safe to read without significant mental wellness concerns."
        )

    return level, message


# =============================================================
# HELPER FUNCTION: Generate an Overall Recommendation
# =============================================================
def get_recommendation(
    sentiment_label: str,
    wellness_impact: str,
    clickbait_score: float
) -> str:
    """Returns a practical recommendation for the reader."""

    if wellness_impact == "HIGH":
        return (
            "Take a break from this type of content. Seek balanced, solution-focused news. "
            "Consider cross-referencing with trusted fact-checking sites."
        )
    elif clickbait_score >= 0.5:
        return (
            "This headline shows signs of clickbait. Read the full article carefully "
            "and check if the content matches the dramatic headline."
        )
    elif sentiment_label == "POSITIVE":
        return (
            "This article has a positive tone. Engaging with uplifting content "
            "can improve focus and reduce news fatigue."
        )
    else:
        return (
            "Stay informed but set healthy limits on news consumption. "
            "Balance with positive content for mental wellness."
        )


# =============================================================
# POST /analyze
#
# The main endpoint. Accepts a news title + description,
# runs them through the AI model and scoring functions,
# and returns a complete analysis report.
#
# How to call it (from Swagger /docs or from the frontend):
#   POST http://127.0.0.1:8000/analyze
#   Content-Type: application/json
#   Body: { "title": "...", "description": "..." }
# =============================================================
@router.post("/", response_model=AnalyzeResponse)
def analyze_news(request: AnalyzeRequest):
    """
    ## AI News Analysis

    Analyzes a news article's title and description using:
    - **HuggingFace DistilBERT** for sentiment classification
    - **Custom keyword analysis** for fear and clickbait scoring
    - **Wellness impact assessment** for mental health awareness

    **Input:** `{ "title": "...", "description": "..." }`

    **Output:** Sentiment, confidence, fear score, clickbait score, wellness impact.
    """

    # -----------------------------------------------
    # Step 1: Check that the AI model is available
    # -----------------------------------------------
    if not MODEL_LOADED or sentiment_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI model is not available. This usually means the transformers "
                "library or model failed to load. Check server logs."
            ),
        )

    # -----------------------------------------------
    # Step 2: Combine title + description into one text
    #
    # We concatenate them with a separator so the model
    # considers both the headline AND the content together.
    # -----------------------------------------------
    combined_text = f"{request.title}. {request.description}"

    # -----------------------------------------------
    # Step 3: Run AI Sentiment Analysis
    #
    # sentiment_pipeline(text) does internally:
    #   1. Tokenize: "Scientists discover..." → [101, 3522, 8569, ...]
    #   2. Forward pass: numbers → model → logits (raw scores)
    #   3. Softmax: logits → probabilities → [0.08, 0.92]
    #   4. Argmax: pick the highest probability label
    #   → Returns: [{"label": "POSITIVE", "score": 0.9234}]
    # -----------------------------------------------
    try:
        # The pipeline returns a list; we take the first (and only) result
        raw_result  = sentiment_pipeline(combined_text)[0]
        # raw_result looks like: {"label": "POSITIVE", "score": 0.9234}

        ai_label    = raw_result["label"]   # "POSITIVE" or "NEGATIVE"
        ai_score    = raw_result["score"]   # Float between 0.0 and 1.0

    except Exception as e:
        logger.error(f"Sentiment inference error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"AI model inference failed: {str(e)}",
        )

    # -----------------------------------------------
    # Step 4: Map the model's binary output to 3-level sentiment
    #
    # DistilBERT only returns POSITIVE or NEGATIVE.
    # We treat low-confidence results as NEUTRAL.
    # -----------------------------------------------
    NEUTRAL_THRESHOLD = 0.65  # Below this confidence = treat as NEUTRAL

    if ai_score < NEUTRAL_THRESHOLD:
        sentiment_label = "NEUTRAL"
    else:
        sentiment_label = ai_label  # "POSITIVE" or "NEGATIVE"

    # -----------------------------------------------
    # Step 5: Run our custom scoring functions
    # -----------------------------------------------
    fear_score      = compute_fear_score(combined_text)
    clickbait_score = compute_clickbait_score(request.title)  # Clickbait is in titles

    # -----------------------------------------------
    # Step 6: Derive higher-level analysis
    # -----------------------------------------------
    emotional_intensity = get_emotional_intensity(ai_score, fear_score)
    wellness_impact, wellness_message = get_wellness_impact(
        sentiment_label, fear_score, clickbait_score
    )
    recommendation = get_recommendation(sentiment_label, wellness_impact, clickbait_score)

    # -----------------------------------------------
    # Step 7: Build and return the structured response
    #
    # FastAPI validates this against AnalyzeResponse schema
    # and automatically serializes it to JSON.
    # -----------------------------------------------
    return AnalyzeResponse(
        # Echo back what was analyzed
        title=request.title,
        description_preview=request.description[:120] + "..." if len(request.description) > 120 else request.description,

        # AI sentiment result
        sentiment={
            "label":              sentiment_label,
            "confidence":         round(ai_score, 4),
            "confidence_percent": f"{ai_score * 100:.1f}%",
        },

        # Custom scoring
        wellness_scores={
            "fear_score":      fear_score,
            "clickbait_score": clickbait_score,
            "wellness_impact": wellness_impact,
            "wellness_message": wellness_message,
        },

        # High-level summary
        summary={
            "overall_tone":       sentiment_label.capitalize(),
            "emotional_intensity": emotional_intensity,
            "recommendation":     recommendation,
        },

        # Metadata
        model_used=MODEL_NAME,
        analysis_version="2.0",
    )
