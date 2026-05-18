# =============================================================
# app/services/topic_extractor.py — Intelligent Topic Extraction
#
# PURPOSE:
#   Convert raw news headlines into focused search topics for
#   Wikipedia lookup.  The problem with sending a raw headline
#   like "Trump warns Iran clock is ticking as peace progress stalls"
#   directly to Wikipedia is that it matches the "Donald Trump"
#   biography page rather than "Iran–United States relations".
#
# SOLUTION:
#   1. Use YAKE (Yet Another Keyword Extractor) to score keywords
#      by their statistical significance in the text.
#   2. Strip noise words (action verbs, adverbs, clickbait terms)
#      that appear in headlines but add no topical meaning.
#   3. Reconstruct a 2–3 word topic phrase from the survivors.
#   4. Fallback to cleaned noun-based extraction if YAKE unavailable.
#
# INSTALL:
#   pip install yake
#
# USAGE:
#   from app.services.topic_extractor import extract_main_topic
#   topic = extract_main_topic("Trump warns Iran clock is ticking")
#   # → "Iran United States relations"
# =============================================================

import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# YAKE — lazy import so the rest of the app still works if yake
# isn't installed yet (graceful degradation to fallback logic).
# ------------------------------------------------------------------
try:
    import yake as _yake
    YAKE_AVAILABLE = True
    logger.info("✅ YAKE keyword extractor loaded successfully.")
except ImportError:
    _yake = None
    YAKE_AVAILABLE = False
    logger.warning("⚠️  yake not installed — topic extractor will use fallback logic.")


# ==============================================================
# NOISE WORD LISTS
#
# These are words that appear very frequently in news headlines
# but tell us nothing about the *topic* of the article.
#
# ACTION/VERB NOISE — verbs journalists use to introduce quotes
# or describe events, e.g. "Trump warns Iran…"
# → "warns" is not part of the topic.
#
# CLICKBAIT NOISE — words used for drama, not information.
#
# TEMPORAL NOISE — time references that pollute Wikipedia slugs.
# ==============================================================

_ACTION_NOISE = {
    "warns", "warn", "warning", "says", "said", "say", "tells", "told",
    "reveal", "reveals", "revealed", "showing", "shows", "show",
    "claims", "claim", "claimed", "slams", "slam", "hits", "hit",
    "calls", "call", "called", "demands", "demand", "urges", "urge",
    "blasts", "blast", "attacks", "attack", "accuses", "accuse",
    "confirms", "confirm", "denies", "deny", "admits", "admit",
    "reports", "report", "reported", "announces", "announce", "announced",
    "threatens", "threaten", "pledges", "pledge", "vows", "vow",
    "refuses", "refuse", "defends", "defend", "backs", "back",
    "slashes", "slash", "cuts", "cut", "raises", "raise",
    "pushes", "push", "faces", "face", "seeks", "seek",
    "calls on", "weighs in", "doubles down", "fires back",
}

_CLICKBAIT_NOISE = {
    "breaking", "exclusive", "shocking", "stunning", "explosive",
    "bombshell", "ticking", "latest", "update", "urgent", "must",
    "see", "watch", "wow", "unbelievable", "incredible", "amazing",
    "sensational", "just", "now", "today", "happening", "live",
    "alert", "developing", "special", "major", "massive", "huge",
    "biggest", "worst", "best", "first", "last", "only",
    "reveals", "surprising", "unexpected", "unprecedented",
}

_TEMPORAL_NOISE = {
    "monday", "tuesday", "wednesday", "thursday", "friday",
    "saturday", "sunday", "january", "february", "march",
    "april", "may", "june", "july", "august", "september",
    "october", "november", "december", "yesterday", "tomorrow",
    "week", "month", "year", "annual", "daily", "weekly",
    "amid", "after", "before", "during", "following",
}

_FILLER_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "not", "no", "nor",
    "so", "yet", "both", "either", "its", "it", "this", "that", "these",
    "those", "as", "if", "than", "then", "about", "over", "under",
    "through", "into", "out", "up", "while", "when", "where", "which",
    "who", "what", "how", "why", "new", "old", "more", "less",
    "within", "without", "against", "between", "among", "around",
    "whether", "although", "despite", "however", "also", "still",
    "ever", "never", "always", "often", "again", "their", "there",
    "they", "them", "we", "us", "our", "he", "she", "him", "her",
    "his", "its", "one", "two", "three", "four", "five",
    "said said", "can", "cannot", "get", "got", "say", "go", "going",
}

# Combined noise set for fast lookup
_ALL_NOISE: set = _ACTION_NOISE | _CLICKBAIT_NOISE | _TEMPORAL_NOISE | _FILLER_WORDS


# ==============================================================
# DOMAIN CONTEXT MAP
#
# Maps common news entities/places to better Wikipedia search
# terms that have a higher chance of finding relevant pages.
#
# Format: set of (trigger_word, replacement_phrase)
# If trigger word is found in headline, we prefer the mapped phrase.
# ==============================================================
_ENTITY_CONTEXT_MAP = {
    # Geopolitical entities → relation pages
    "iran":          "Iran United States relations",
    "russia":        "Russia politics economy",
    "ukraine":       "Ukraine war conflict",
    "china":         "China economy geopolitics",
    "israel":        "Israel Palestine conflict",
    "gaza":          "Gaza conflict Palestine",
    "nato":          "NATO alliance military",
    "taiwan":        "Taiwan China relations",
    "north korea":   "North Korea nuclear weapons",
    "south korea":   "South Korea economy",
    # Economic entities
    "bitcoin":       "Bitcoin cryptocurrency",
    "crypto":        "cryptocurrency blockchain",
    "fed":           "Federal Reserve monetary policy",
    "inflation":     "inflation monetary policy",
    "recession":     "economic recession",
    "oil":           "oil prices energy market",
    "gold":          "gold prices commodity market",
    "stock market":  "stock market economy",
    # Technology
    "ai":            "artificial intelligence",
    "chatgpt":       "ChatGPT artificial intelligence",
    "openai":        "OpenAI artificial intelligence",
    "tesla":         "Tesla electric vehicles",
    "apple":         "Apple technology",
    "meta":          "Meta social media technology",
    # Health
    "covid":         "COVID-19 pandemic",
    "vaccine":       "vaccine public health",
    "cancer":        "cancer treatment medicine",
    # Climate
    "climate":       "climate change global warming",
    "carbon":        "carbon emissions climate policy",
}


# ==============================================================
# PUBLIC API
# ==============================================================

def extract_main_topic(text: str) -> str:
    """
    Extract the most relevant 2–3 word topic from a news headline.

    Strategy:
      1. Check entity context map for direct mappings (fast path)
      2. Use YAKE to score keywords statistically (if available)
      3. Filter noise words from candidates
      4. Reconstruct a clean 2–3 word topic phrase
      5. Fallback to simple noun extraction if all else fails

    Parameters
    ----------
    text : str
        Raw news headline or topic string.

    Returns
    -------
    str
        A clean, focused 2–3 word topic string suitable for Wikipedia lookup.
        Examples:
          "Trump warns Iran clock is ticking" → "Iran United States relations"
          "Gold prices rise amid uncertainty"  → "gold prices commodity"
          "AI breakthrough: ChatGPT beats humans" → "ChatGPT artificial intelligence"
    """

    if not text or not text.strip():
        return "general news"

    text_clean = text.strip()
    text_lower = text_clean.lower()

    # -------------------------------------------------------
    # Step 1: Entity context map fast-path
    # If we recognise a strong entity, return the mapped phrase
    # directly — this gives the best Wikipedia hit rate.
    # -------------------------------------------------------
    for entity, mapped_topic in _ENTITY_CONTEXT_MAP.items():
        # Word-boundary match to avoid "Iran" matching "Iranian"
        pattern = r"\b" + re.escape(entity) + r"\b"
        if re.search(pattern, text_lower):
            logger.debug("Topic extractor: entity map match %r → %r", entity, mapped_topic)
            return mapped_topic

    # -------------------------------------------------------
    # Step 2: YAKE extraction (if available)
    # YAKE scores n-grams (1–3 word phrases) by:
    #   - Word frequency and position
    #   - Casing (proper nouns score higher)
    #   - Co-occurrence patterns
    # Lower YAKE score = more important keyword.
    # -------------------------------------------------------
    if YAKE_AVAILABLE and _yake is not None:
        try:
            kw_extractor = _yake.KeywordExtractor(
                lan="en",
                n=2,           # Extract up to 2-gram phrases
                dedupLim=0.7,  # Deduplicate similar keywords
                top=8,         # Get top 8 candidates
                features=None,
            )
            yake_keywords = kw_extractor.extract_keywords(text_clean)
            # yake_keywords: list of (keyword_string, score) — lower score = better

            # Filter noise from YAKE results
            filtered = [
                kw for kw, score in yake_keywords
                if _is_meaningful(kw)
            ]

            if filtered:
                # Take top 2 YAKE keywords and combine them
                topic = " ".join(filtered[:2])
                logger.debug("Topic extractor: YAKE result %r → %r", text_clean, topic)
                return topic

        except Exception as e:
            logger.warning("YAKE extraction failed, using fallback: %s", e)

    # -------------------------------------------------------
    # Step 3: Fallback — cleaned noun extraction
    # Split on words, filter noise, pick capitalized (proper
    # noun) words first, then fill from content words.
    # -------------------------------------------------------
    return _fallback_extraction(text_clean)


# ==============================================================
# PRIVATE HELPERS
# ==============================================================

def _is_meaningful(phrase: str) -> bool:
    """
    Return True if a keyword phrase passes our noise filter.

    Checks that:
    - The phrase is at least 3 characters long
    - No word in the phrase is a known noise word
    - The phrase contains at least one alphabetic character
    """
    if len(phrase) < 3:
        return False

    words = phrase.lower().split()
    for word in words:
        if word in _ALL_NOISE:
            return False
        # Also reject if it's purely numeric
        if word.isdigit():
            return False

    return bool(re.search(r"[a-zA-Z]", phrase))


def _fallback_extraction(text: str) -> str:
    """
    Simple fallback: extract meaningful words from the headline
    without using any external library.

    Returns a 2–3 word topic string.
    """
    tokens = re.findall(r"[a-zA-Z]+", text)

    proper_nouns: List[str] = []
    content_words: List[str] = []

    for tok in tokens:
        lower = tok.lower()
        if lower in _ALL_NOISE or len(lower) < 3:
            continue
        if tok[0].isupper():
            proper_nouns.append(lower)
        else:
            content_words.append(lower)

    # Deduplicate while preserving order
    seen: set = set()
    ordered: List[str] = []
    for w in proper_nouns + content_words:
        if w not in seen:
            seen.add(w)
            ordered.append(w)

    if not ordered:
        return text[:50]  # Last resort: first 50 chars of original

    return " ".join(ordered[:3])


def get_wikipedia_search_candidates(topic: str) -> List[str]:
    """
    Given a cleaned topic string, return an ordered list of Wikipedia
    slug candidates to try (most specific → least specific).

    This is the multi-attempt strategy used by context_service.py
    to maximise the chance of finding a real Wikipedia page.

    Parameters
    ----------
    topic : str
        The output of extract_main_topic() — a clean 2–3 word phrase.

    Returns
    -------
    list of str
        Wikipedia URL slugs (spaces replaced by underscores).
        Try each in order; use the first one that returns a real page.

    Example
    -------
    topic = "Iran United States relations"
    → [
        "Iran_United_States_relations",   # full phrase (best)
        "Iran_United_States",             # first 2 words
        "Iran",                           # first word (broadest)
      ]
    """
    words = topic.split()
    candidates: List[str] = []

    # Candidate 1: full topic (most specific)
    full = "_".join(words)
    if full:
        candidates.append(full)

    # Candidate 2: first 3 words
    if len(words) >= 3:
        candidates.append("_".join(words[:3]))

    # Candidate 3: first 2 words
    if len(words) >= 2:
        candidates.append("_".join(words[:2]))

    # Candidate 4: first word only (broadest match)
    if words:
        candidates.append(words[0])

    # Deduplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for c in candidates:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            unique.append(c)

    return unique
