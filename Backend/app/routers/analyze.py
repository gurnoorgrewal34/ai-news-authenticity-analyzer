# =============================================================
# app/routers/analyze.py — Module 2: AI News Analysis Engine (v2)
#
# WHAT CHANGED IN v2:
#   - Added compute_fake_news_risk()  → LOW / MEDIUM / HIGH
#   - Added get_emotional_framing()   → Neutral / Fear-driven /
#                                       Emotionally Charged / Sensationalized
#   - Saves quick_summary + reading_time_label to SQLite
#   - Returns new ai_flags section in response
#   - All existing logic fully preserved
# =============================================================

import re
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.analyze import AnalyzeRequest, AnalyzeResponse
from app.database import get_db
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analyze",
    tags=["Analysis"],
)


# =============================================================
# MODEL LOADING — Load HuggingFace pipelines ONCE at startup
# =============================================================

try:
    from transformers import pipeline as hf_pipeline

    sentiment_pipeline = hf_pipeline(
        "sentiment-analysis",
        model="distilbert-base-uncased-finetuned-sst-2-english",
        truncation=True,
        max_length=512,
    )
    MODEL_LOADED = True
    MODEL_NAME   = "distilbert-base-uncased-finetuned-sst-2-english"
    logger.info("✅ Sentiment model loaded.")

except Exception as e:
    sentiment_pipeline = None
    MODEL_LOADED       = False
    MODEL_NAME         = "unavailable"
    logger.error(f"❌ Sentiment model failed: {e}")


try:
    from transformers import pipeline as hf_pipeline

    summarizer_pipeline = hf_pipeline(
        "summarization",
        model="sshleifer/distilbart-cnn-12-6",
        truncation=True,
    )
    SUMMARIZER_LOADED = True
    SUMMARIZER_NAME   = "sshleifer/distilbart-cnn-12-6"
    logger.info("✅ Summarization model loaded.")

except Exception as e:
    summarizer_pipeline = None
    SUMMARIZER_LOADED   = False
    SUMMARIZER_NAME     = "unavailable"
    logger.warning(f"⚠️  Summarization model not loaded: {e}")


# =============================================================
# KEYWORD LISTS
# =============================================================

FEAR_KEYWORDS = [
    "crisis", "disaster", "attack", "war", "threat", "danger", "deadly",
    "collapse", "emergency", "catastrophe", "terror", "explosion", "shooting",
    "outbreak", "epidemic", "pandemic", "death", "killed", "fatal", "severe",
    "alarming", "warning", "devastating", "tragic", "shocking", "horrific",
    "violence", "murder", "accident", "crash", "flood", "earthquake", "fire",
    "bomb", "weapon", "hostage", "corruption", "fraud", "scandal", "arrested",
]

FINANCE_KEYWORDS = [
    "stock", "stocks", "market", "markets", "gold", "silver", "finance",
    "economy", "economic", "business", "oil", "exports", "trade",
    "investment", "investments", "shares", "equity", "bonds", "gdp",
    "inflation", "interest rate", "revenue", "profit", "fiscal", "monetary",
    "commodity", "commodities", "exchange", "currency", "crypto", "bitcoin",
]

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
    r"\b\d+ (ways|things|reasons|facts|tips)\b",
]

# Sensational words used in fake-news risk detection
SENSATIONAL_WORDS = [
    "exposed", "explosive", "bombshell", "coverup", "cover-up", "conspiracy",
    "hoax", "fake", "lie", "lies", "lied", "corrupt", "corruption",
    "rigged", "stolen", "manipulation", "manipulated", "propaganda",
    "crisis actor", "false flag", "deep state", "plandemic", "scam",
    "they don't want", "wake up", "sheeple", "censored", "banned",
    "silenced", "truth", "real truth", "what they hide",
]


# =============================================================
# HELPER: Fear Score
# =============================================================

def compute_fear_score(text: str) -> float:
    """Returns 0.0–1.0 fear keyword density score."""
    text_lower = text.lower()
    fear_count = sum(1 for word in FEAR_KEYWORDS if word in text_lower)
    return round(min(fear_count / 5, 1.0), 2)


# =============================================================
# HELPER: Clickbait Score
# =============================================================

def compute_clickbait_score(title: str) -> float:
    """Returns 0.0–1.0 clickbait pattern score."""
    title_lower = title.lower()
    matches = sum(1 for p in CLICKBAIT_PATTERNS if re.search(p, title_lower))
    return round(min(matches / 4, 1.0), 2)


# =============================================================
# HELPER: Finance Article Detection
# =============================================================

def is_finance_article(text: str) -> bool:
    """Returns True if the text contains finance/business keywords."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in FINANCE_KEYWORDS)


# =============================================================
# HELPER: Emotional Intensity
# =============================================================

def get_emotional_intensity(confidence: float, fear_score: float) -> str:
    """Returns 'Low', 'Moderate', or 'High'."""
    combined = (confidence + fear_score) / 2
    if combined >= 0.70:
        return "High"
    elif combined >= 0.40:
        return "Moderate"
    return "Low"


# =============================================================
# HELPER: Wellness Impact
# =============================================================

def get_wellness_impact(
    sentiment_label:    str,
    fear_score:         float,
    clickbait_score:    float,
    finance_overridden: bool = False,
) -> tuple[str, str]:
    """Returns (impact_level, message)."""

    if finance_overridden:
        return (
            "LOW",
            "📊 This appears to be a financial or business news article. "
            "Words like 'fall', 'drop', or 'decline' are standard financial "
            "reporting language and do not indicate genuine negativity or harm. "
            "Sentiment has been adjusted to Neutral for a more accurate reading.",
        )

    is_negative  = sentiment_label == "NEGATIVE"
    is_fearful   = fear_score >= 0.5
    is_clickbait = clickbait_score >= 0.5

    if is_negative and is_fearful:
        return (
            "HIGH",
            "⚠️ This article contains strong negative and fear-inducing language. "
            "Consider verifying with multiple sources before forming strong opinions. "
            "Limit exposure to highly stressful news for mental well-being.",
        )
    elif is_negative or is_fearful or is_clickbait:
        return (
            "MODERATE",
            "🔔 This article has some negative or emotionally charged language. "
            "Read critically and be mindful of how news consumption affects your mood.",
        )
    return (
        "LOW",
        "✅ This article appears to have a neutral or positive tone. "
        "It is likely safe to read without significant mental wellness concerns.",
    )


# =============================================================
# HELPER: Recommendation
# =============================================================

def get_recommendation(
    sentiment_label: str,
    wellness_impact: str,
    clickbait_score: float,
) -> str:
    """Returns a practical reading recommendation."""
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
    return (
        "Stay informed but set healthy limits on news consumption. "
        "Balance with positive content for mental wellness."
    )


# =============================================================
# HELPER: Generate AI Summary
# =============================================================

def generate_summary(text: str) -> tuple[str, bool]:
    """Returns (summary_text, used_ai_model)."""
    word_count = len(text.split())

    if SUMMARIZER_LOADED and summarizer_pipeline is not None and word_count >= 30:
        try:
            max_len = min(130, max(40, word_count // 3))
            result  = summarizer_pipeline(
                text, max_length=max_len, min_length=30,
                do_sample=False, truncation=True,
            )
            return result[0]["summary_text"].strip(), True
        except Exception as e:
            logger.warning(f"Summarizer fallback: {e}")

    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if len(s.split()) >= 5]
    fallback  = " ".join(sentences[:2])
    if not fallback:
        fallback = text[:280] + ("..." if len(text) > 280 else "")
    return fallback, False


# =============================================================
# HELPER: Extract Key Points
# =============================================================

def extract_key_points(text: str, max_points: int = 4) -> list[str]:
    """Returns 3–5 key sentences using position + content heuristics."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    sentences = [s.strip() for s in sentences if 5 <= len(s.split()) <= 50]

    if not sentences:
        return ["Not enough content to extract key points."]

    total = len(sentences)

    def score(idx: int, sent: str) -> float:
        s = 0.0
        if idx == 0:         s += 3.0
        if idx == 1:         s += 1.0
        if idx == total - 1: s += 1.5
        if re.search(r"\d+", sent): s += 0.8
        return s

    ranked  = sorted(range(total), key=lambda i: -score(i, sentences[i]))
    top_idx = sorted(ranked[:max_points])
    return [sentences[i] for i in top_idx]


# =============================================================
# HELPER: Estimate Reading Time
# =============================================================

def estimate_reading_time(text: str) -> tuple[int, str]:
    """Returns (seconds, label)."""
    WORDS_PER_MINUTE = 238
    word_count = len(text.split())
    seconds    = max(10, int((word_count / WORDS_PER_MINUTE) * 60))

    if seconds < 60:
        label = f"about {seconds} seconds"
    elif seconds < 120:
        label = "about 1 minute"
    else:
        label = f"about {round(seconds / 60)} minutes"

    return seconds, label


# =============================================================
# HELPER: Emotional Label
# =============================================================

def get_emotional_label(
    sentiment_label:    str,
    fear_score:         float,
    confidence:         float,
    clickbait_score:    float,
    finance_overridden: bool,
) -> tuple[str, str]:
    """Returns (emotional_label, emotional_description)."""

    if finance_overridden:
        return (
            "📊 Informative & Factual",
            "This is financial or business reporting. "
            "Market-movement words like 'fall' or 'drop' are neutral in this context.",
        )

    if sentiment_label == "POSITIVE":
        if fear_score < 0.2 and confidence >= 0.75:
            return (
                "😊 Uplifting & Positive",
                "The article has an encouraging, optimistic tone with no alarming signals.",
            )
        return (
            "🙂 Mildly Positive",
            "The article leans positive but may contain some cautionary elements.",
        )

    if sentiment_label == "NEGATIVE":
        if fear_score >= 0.5 and clickbait_score >= 0.5:
            return (
                "😱 Alarming & Sensational",
                "Strong negative framing combined with clickbait tactics. Verify before sharing.",
            )
        if fear_score >= 0.5:
            return (
                "😟 Concerning & Distressing",
                "The article contains alarming language that may cause anxiety. Read mindfully.",
            )
        if clickbait_score >= 0.5:
            return (
                "🎭 Dramatic & Exaggerated",
                "Clickbait tactics detected. The headline may be more dramatic than the content.",
            )
        return (
            "😐 Negatively Framed",
            "The article has a negative tone but without extreme fear or clickbait signals.",
        )

    if clickbait_score >= 0.5:
        return (
            "🤔 Neutral but Clickbait-y",
            "Content is relatively balanced, but the headline uses sensationalist language.",
        )
    return (
        "😐 Balanced & Neutral",
        "The article presents information in a calm, factual, and balanced tone.",
    )


# =============================================================
# NEW: Fake News Risk Indicator  (Phase 7)
# =============================================================

def compute_fake_news_risk(
    title:          str,
    combined_text:  str,
    fear_score:     float,
    clickbait_score: float,
    sentiment_label: str,
    confidence:     float,
) -> tuple[str, str]:
    """
    Compute a Fake News Risk level: LOW | MEDIUM | HIGH.

    Based on:
      - Sensational / conspiracy language in title + text
      - High fear AND high clickbait together
      - Extreme confidence on a NEGATIVE sentiment (model very sure → suspicious)
      - Excessive emotional manipulation patterns

    Returns
    -------
    (risk_level, reason)
        risk_level : "LOW" | "MEDIUM" | "HIGH"
        reason     : short explanation for the user
    """
    text_lower  = (title + " " + combined_text).lower()

    # Count sensational words
    sensational_count = sum(
        1 for word in SENSATIONAL_WORDS if word in text_lower
    )

    # Signal scoring
    signals = 0
    reasons = []

    if clickbait_score >= 0.5:
        signals += 1
        reasons.append("clickbait headline")

    if fear_score >= 0.6:
        signals += 1
        reasons.append("high fear language")

    if sensational_count >= 2:
        signals += 2
        reasons.append(f"{sensational_count} sensational/conspiracy terms")
    elif sensational_count == 1:
        signals += 1
        reasons.append("sensational language")

    if sentiment_label == "NEGATIVE" and confidence >= 0.90 and fear_score >= 0.5:
        signals += 1
        reasons.append("extreme negative framing")

    # All caps words in title (shouting = manipulation)
    caps_words = len([w for w in title.split() if w.isupper() and len(w) > 2])
    if caps_words >= 2:
        signals += 1
        reasons.append("all-caps words in headline")

    # Assign risk level
    if signals >= 4:
        level = "HIGH"
        prefix = "Multiple red flags detected: "
    elif signals >= 2:
        level = "MEDIUM"
        prefix = "Some credibility concerns: "
    else:
        level = "LOW"
        prefix = "No significant fake news indicators detected."

    if reasons and signals >= 2:
        reason = prefix + ", ".join(reasons) + "."
    else:
        reason = prefix

    return level, reason


# =============================================================
# NEW: Emotional Framing Detector  (Phase 7)
# =============================================================

def get_emotional_framing(
    sentiment_label:    str,
    fear_score:         float,
    clickbait_score:    float,
    finance_overridden: bool,
) -> str:
    """
    Classify the article's primary emotional framing style.

    Returns one of:
      - "Neutral"            — balanced, factual, minimal emotional language
      - "Fear-driven"        — heavy use of fear/alarm language
      - "Emotionally Charged"— strong sentiment (positive or negative)
                               but not necessarily manipulative
      - "Sensationalized"    — clickbait + high emotional content together
    """
    if finance_overridden:
        return "Neutral"

    is_high_fear      = fear_score >= 0.5
    is_high_clickbait = clickbait_score >= 0.5
    is_strong_sent    = sentiment_label in ("POSITIVE", "NEGATIVE")

    if is_high_clickbait and (is_high_fear or is_strong_sent):
        return "Sensationalized"

    if is_high_fear:
        return "Fear-driven"

    if is_strong_sent:
        return "Emotionally Charged"

    return "Neutral"


# =============================================================
# POST /analyze — Main Endpoint
# =============================================================

@router.post("/", response_model=AnalyzeResponse)
def analyze_news(request: AnalyzeRequest, db: Session = Depends(get_db)):
    """
    ## AI News Analysis

    Analyzes a news article using:
    - **HuggingFace DistilBERT** — sentiment classification
    - **Custom keyword analysis** — fear and clickbait scoring
    - **Wellness impact assessment** — mental health awareness
    - **Fake News Risk Indicator** — NEW: LOW / MEDIUM / HIGH
    - **Emotional Framing Detector** — NEW: Neutral / Fear-driven / Sensationalized
    """

    # Step 1: Guard — model available?
    if not MODEL_LOADED or sentiment_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI model is not available. The transformers library or model "
                "failed to load. Check server logs."
            ),
        )

    # Step 2: Combine text
    combined_text = f"{request.title}. {request.description}"

    # Step 3: Run AI sentiment
    try:
        raw_result  = sentiment_pipeline(combined_text)[0]
        ai_label    = raw_result["label"]
        ai_score    = raw_result["score"]
    except Exception as e:
        logger.error(f"Sentiment inference error: {e}")
        raise HTTPException(status_code=500, detail=f"AI model inference failed: {e}")

    # Step 4: Map to 3-level sentiment
    NEUTRAL_THRESHOLD = 0.65
    sentiment_label   = ai_label if ai_score >= NEUTRAL_THRESHOLD else "NEUTRAL"

    # Step 5: Custom scoring
    fear_score      = compute_fear_score(combined_text)
    clickbait_score = compute_clickbait_score(request.title)

    # Step 5b: Finance override
    finance_overridden = False
    FINANCE_CONF_THRESHOLD = 0.65
    FINANCE_FEAR_THRESHOLD = 0.3

    if (
        sentiment_label == "NEGATIVE"
        and ai_score >= FINANCE_CONF_THRESHOLD
        and fear_score < FINANCE_FEAR_THRESHOLD
        and is_finance_article(combined_text)
    ):
        sentiment_label    = "NEUTRAL"
        finance_overridden = True
        logger.info(f"📊 Finance override: NEGATIVE→NEUTRAL (conf={ai_score:.2f}, fear={fear_score})")

    # Step 6: Higher-level analysis
    emotional_intensity = get_emotional_intensity(ai_score, fear_score)
    wellness_impact, wellness_message = get_wellness_impact(
        sentiment_label, fear_score, clickbait_score,
        finance_overridden=finance_overridden,
    )
    recommendation = get_recommendation(sentiment_label, wellness_impact, clickbait_score)

    # Step 6b: Article intelligence
    quick_summary, summarizer_used              = generate_summary(combined_text)
    key_points                                  = extract_key_points(combined_text)
    reading_time_seconds, reading_time_label    = estimate_reading_time(combined_text)
    emotional_label, emotional_description      = get_emotional_label(
        sentiment_label, fear_score, ai_score, clickbait_score, finance_overridden
    )

    # Step 6c: NEW — Fake News Risk + Emotional Framing
    fake_news_risk, fake_news_reason = compute_fake_news_risk(
        title           = request.title,
        combined_text   = combined_text,
        fear_score      = fear_score,
        clickbait_score = clickbait_score,
        sentiment_label = sentiment_label,
        confidence      = ai_score,
    )
    emotional_framing = get_emotional_framing(
        sentiment_label, fear_score, clickbait_score, finance_overridden
    )

    # Step 6d: Save to SQLite
    try:
        crud.create_analysis_record(
            db,
            keyword             = request.keyword,
            title               = request.title,
            source              = request.source,
            sentiment           = sentiment_label,
            confidence          = ai_score,
            fear_score          = fear_score,
            clickbait_score     = clickbait_score,
            wellness_impact     = wellness_impact,
            emotional_label     = emotional_label,
            quick_summary       = quick_summary,
            reading_time_label  = reading_time_label,
        )
        logger.info(f"💾 Saved to DB: '{request.title[:40]}'")
    except Exception as db_err:
        logger.error(f"❌ DB save failed (non-blocking): {db_err}")

    # Step 7: Build and return response
    return AnalyzeResponse(
        title               = request.title,
        description_preview = (
            request.description[:120] + "..."
            if len(request.description) > 120
            else request.description
        ),

        sentiment = {
            "label":              sentiment_label,
            "confidence":         round(ai_score, 4),
            "confidence_percent": f"{ai_score * 100:.1f}%",
        },

        wellness_scores = {
            "fear_score":      fear_score,
            "clickbait_score": clickbait_score,
            "wellness_impact": wellness_impact,
            "wellness_message": wellness_message,
        },

        summary = {
            "overall_tone":        sentiment_label.capitalize(),
            "emotional_intensity": emotional_intensity,
            "recommendation":      recommendation,
        },

        article_insights = {
            "quick_summary":         quick_summary,
            "key_points":            key_points,
            "reading_time_seconds":  reading_time_seconds,
            "reading_time_label":    reading_time_label,
            "emotional_label":       emotional_label,
            "emotional_description": emotional_description,
            "summarizer_used":       summarizer_used,
        },

        # NEW in v2
        ai_flags = {
            "fake_news_risk":        fake_news_risk,
            "emotional_framing":     emotional_framing,
            "fake_news_risk_reason": fake_news_reason,
        },

        model_used       = MODEL_NAME,
        analysis_version = "4.0",
    )
