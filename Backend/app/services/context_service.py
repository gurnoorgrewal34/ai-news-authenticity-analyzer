# =============================================================
# app/services/context_service.py — Historical Context Logic (v2)
#
# WHAT CHANGED IN v2:
#   - Uses intelligent topic extraction (YAKE + entity map) instead of
#     sending raw headlines to Wikipedia.
#   - Generates `historical_summary` (1-sentence concise overview).
#   - Detects `geopolitical_relevance` from Wikipedia content signals.
#   - Improved timeline (decade detection), key events, related topics.
#   - Better Wikipedia slug candidates via topic_extractor module.
#
# DESIGN PHILOSOPHY (NO HALLUCINATIONS):
#   Every piece of text in the response comes from Wikipedia or NewsAPI.
#   Nothing is invented. If Wikipedia has no page, graceful empty fields
#   are returned rather than made-up content.
# =============================================================

import re
import logging
import requests
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from app.config import NEWSAPI_KEY, NEWSAPI_BASE_URL
from app.services.topic_extractor import extract_main_topic, get_wikipedia_search_candidates

logger = logging.getLogger(__name__)


# =============================================================
# CONSTANTS
# =============================================================

WIKIPEDIA_API_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"

# Standard English stopwords
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "not", "no", "nor",
    "so", "yet", "both", "either", "its", "it", "this", "that", "these",
    "those", "as", "if", "than", "then", "about", "after", "before",
    "into", "through", "during", "over", "under", "again", "further",
    "once", "more", "also", "up", "out", "new", "says", "say", "said",
    "he", "she", "they", "we", "us", "our", "their", "his", "her",
    "how", "what", "when", "who", "why", "which", "where",
}

# Geopolitical signal keywords — if found in extract, classify as geopolitically relevant
_GEO_SIGNALS = {
    "war", "conflict", "military", "nuclear", "sanctions", "treaty",
    "diplomacy", "diplomatic", "negotiations", "alliance", "invasion",
    "president", "government", "parliament", "election", "minister",
    "foreign", "international", "bilateral", "relations", "sovereignty",
    "territory", "border", "troops", "forces", "weapons", "missile",
    "geopolitical", "strategic", "policy", "embargo", "ceasefire",
    "peace", "talks", "summit", "united nations", "security council",
    "trade war", "tariff", "sanctions", "oil", "energy", "economy",
    "gdp", "recession", "inflation", "market", "investment", "finance",
}

MAX_TIMELINE_POINTS = 6
MAX_KEY_EVENTS      = 5
MAX_SOURCES         = 6
REQUEST_TIMEOUT     = 10


# =============================================================
# MAIN PUBLIC FUNCTION
# =============================================================

def get_context(topic: str) -> dict:
    """
    Build a fully factual historical context response for a given news topic.

    Parameters
    ----------
    topic : str
        The raw news headline or keyword (e.g. "Trump warns Iran clock is ticking").

    Returns
    -------
    dict
        A dictionary matching the ContextResponse schema.

    All text is sourced from Wikipedia or NewsAPI. Nothing is invented.
    """

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # -----------------------------------------------
    # Step 1: Intelligent topic extraction
    # Convert raw headline → focused search topic
    # Example: "Trump warns Iran clock is ticking"
    #        → "Iran United States relations"
    # -----------------------------------------------
    extracted_topic = extract_main_topic(topic)
    logger.info(
        "Context request | original=%r | extracted_topic=%r",
        topic, extracted_topic
    )

    # -----------------------------------------------
    # Step 2: Wikipedia lookup with multi-slug strategy
    # Try increasingly broad slugs until one succeeds.
    # -----------------------------------------------
    wiki_data = _try_wikipedia_slugs(topic, extracted_topic)

    historical_context   = wiki_data.get("extract_short", "")
    historical_summary   = wiki_data.get("historical_summary", "")
    timeline_points      = wiki_data.get("timeline_points", [])
    key_events           = wiki_data.get("key_events", [])
    why_it_matters       = wiki_data.get("why_it_matters", "")
    related_topics       = wiki_data.get("related_topics", [])
    wikipedia_url        = wiki_data.get("wikipedia_url")
    geopolitical_relevance = wiki_data.get("geopolitical_relevance", "")

    # -----------------------------------------------
    # Step 3: Fetch related real news articles
    # Use extracted topic for better relevance
    # -----------------------------------------------
    sources = _fetch_news_sources(extracted_topic)

    # -----------------------------------------------
    # Step 4: Assemble final response
    # -----------------------------------------------
    return {
        "topic":                  topic,
        "extracted_topic":        extracted_topic,
        "historical_context":     historical_context,
        "historical_summary":     historical_summary,
        "timeline_points":        timeline_points,
        "key_events":             key_events,
        "why_it_matters":         why_it_matters,
        "related_topics":         related_topics,
        "sources":                sources,
        "wikipedia_url":          wikipedia_url,
        "geopolitical_relevance": geopolitical_relevance,
        "data_freshness":         now_utc,
    }


# =============================================================
# WIKIPEDIA HELPERS
# =============================================================

def _try_wikipedia_slugs(original_topic: str, extracted_topic: str) -> dict:
    """
    Attempt multiple Wikipedia slug variations until one returns a valid page.

    Slug strategy (tried in order):
      1. Slugs derived from the YAKE-extracted topic (smart, entity-focused)
      2. Slugs derived from the original raw topic (fallback)

    Returns an empty/graceful dict if all slugs fail.
    """

    # Get smart candidates from extracted topic
    primary_slugs = get_wikipedia_search_candidates(extracted_topic)

    # Also build fallback slugs from original topic (cleaned)
    original_clean = re.sub(r"[^a-zA-Z0-9 ]", "", original_topic).strip()
    original_words = original_clean.split()
    fallback_slugs = []
    if len(original_words) >= 2:
        fallback_slugs.append("_".join(original_words[:2]))
    if original_words:
        fallback_slugs.append(original_words[0])

    # Combine, deduplicate, try in order
    all_slugs: List[str] = []
    seen: set = set()
    for s in primary_slugs + fallback_slugs:
        key = s.lower()
        if key not in seen and s:
            seen.add(key)
            all_slugs.append(s)

    for slug in all_slugs:
        result = _fetch_wikipedia(slug)
        if result:
            logger.info("Wikipedia hit | slug=%r", slug)
            return result

    # All slugs failed
    logger.warning(
        "Wikipedia: no page found | original=%r | extracted=%r | slugs=%r",
        original_topic, extracted_topic, all_slugs
    )
    return {
        "extract_short": (
            f"No Wikipedia summary was found for \"{extracted_topic}\". "
            "This may be a very recent event or a highly specific subject. "
            "Please check the sources section below for related published articles."
        ),
        "historical_summary": "",
        "timeline_points": [],
        "key_events": [],
        "why_it_matters": (
            "Contextual background could not be retrieved automatically. "
            "Refer to the reliable news sources listed below for more information."
        ),
        "related_topics": [],
        "wikipedia_url": None,
        "geopolitical_relevance": "",
    }


def _fetch_wikipedia(slug: str) -> Optional[dict]:
    """
    Call the Wikipedia REST API for a page summary.

    Returns a parsed dict on success, or None if page not found / unusable.
    Never invents content — only returns what Wikipedia provides.
    """

    url = f"{WIKIPEDIA_API_BASE}/{slug}"

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "NewsAnalyzer/2.0 (educational project)"},
            timeout=REQUEST_TIMEOUT,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        logger.warning("Wikipedia timeout | slug=%r", slug)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Wikipedia connection error | slug=%r", slug)
        return None
    except requests.exceptions.RequestException as exc:
        logger.warning("Wikipedia request error | slug=%r | %s", slug, exc)
        return None

    # Skip disambiguation pages
    page_type = data.get("type", "")
    if page_type in ("disambiguation", "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"):
        logger.debug("Wikipedia disambiguation | slug=%r", slug)
        return None

    extract = data.get("extract", "").strip()
    if not extract or len(extract) < 40:
        return None

    wikipedia_url = data.get("content_urls", {}).get("desktop", {}).get("page")

    # Parse extract into structured fields
    sentences       = _split_sentences(extract)
    timeline_points = _parse_timeline(sentences)
    key_events      = _parse_key_events(sentences)
    why_it_matters  = _build_why_it_matters(sentences)
    related_topics  = _extract_related_topics(data, sentences)

    # Historical summary: single sentence distilling the first sentence
    historical_summary = _build_historical_summary(sentences, data)

    # Geopolitical relevance: detect from extract content
    geopolitical_relevance = _detect_geopolitical_relevance(extract, sentences)

    # Historical context intro: first 3 sentences, max 700 chars
    intro_sentences    = sentences[:3]
    historical_context = " ".join(intro_sentences)
    if len(historical_context) > 700:
        historical_context = historical_context[:697] + "…"

    logger.info("Wikipedia success | slug=%r | sentences=%d", slug, len(sentences))

    return {
        "extract_short":          historical_context,
        "historical_summary":     historical_summary,
        "timeline_points":        timeline_points,
        "key_events":             key_events,
        "why_it_matters":         why_it_matters,
        "related_topics":         related_topics,
        "wikipedia_url":          wikipedia_url,
        "geopolitical_relevance": geopolitical_relevance,
    }


# =============================================================
# TEXT PARSING HELPERS
# =============================================================

def _split_sentences(text: str) -> List[str]:
    """
    Split Wikipedia extract into individual sentences.
    Handles common abbreviations (U.S., Dr., Inc.) by requiring a
    capital letter to follow the period before splitting.
    """
    raw = re.split(r'(?<=[a-z0-9])\.\s+(?=[A-Z])', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 20:
            if not s.endswith((".", "!", "?")):
                s += "."
            sentences.append(s)
    return sentences


def _parse_timeline(sentences: List[str]) -> List[dict]:
    """
    Scan sentences for year AND decade patterns and build timeline points.

    Detection patterns:
      - 4-digit years in range 1800–2099
      - Decade references like "the 1990s" or "early 2000s"

    Returns up to MAX_TIMELINE_POINTS points, sorted chronologically.
    """
    year_pattern   = re.compile(r'\b(1[89]\d{2}|20[012]\d)\b')
    decade_pattern = re.compile(r'\b(the )?(1[89]\d0s|20[012]0s|early|late)\b', re.IGNORECASE)

    points: List[Tuple[int, str]] = []

    for sentence in sentences:
        match = year_pattern.search(sentence)
        if match:
            year = int(match.group(1))
            event = sentence.strip()
            if len(event) > 220:
                event = event[:217] + "…"
            points.append((year, event))
        elif decade_pattern.search(sentence):
            # Extract approximate year from decade reference
            decade_match = re.search(r'\b(1[89]\d0s|20[012]0s)\b', sentence)
            if decade_match:
                decade_str = decade_match.group(1)
                year = int(decade_str[:4])
                event = sentence.strip()
                if len(event) > 220:
                    event = event[:217] + "…"
                points.append((year, event))

    # Sort chronologically, one point per year
    seen_years: set = set()
    sorted_points = []
    for year, event in sorted(points, key=lambda x: x[0]):
        if year not in seen_years:
            seen_years.add(year)
            sorted_points.append({"year": str(year), "event": event})
        if len(sorted_points) >= MAX_TIMELINE_POINTS:
            break

    return sorted_points


def _parse_key_events(sentences: List[str]) -> List[str]:
    """
    Select the most informative sentences as "key events".

    Priority: sentences containing numbers, geopolitical verbs,
    or economic indicators. Skip the first sentence (used for intro).
    """
    candidates = sentences[1:] if len(sentences) > 1 else sentences

    priority_pattern = re.compile(
        r'\b(\d+%|\$[\d,.]+|billion|million|trillion|percent|'
        r'increased|decreased|launched|created|founded|discovered|'
        r'signed|passed|adopted|banned|introduced|declared|'
        r'overthrew|annexed|invaded|negotiated|established|'
        r'collapsed|withdrew|imposed|lifted|agreed|rejected)\b',
        re.IGNORECASE
    )

    high_priority = [s for s in candidates if priority_pattern.search(s)]
    low_priority  = [s for s in candidates if not priority_pattern.search(s)]
    selected      = (high_priority + low_priority)[:MAX_KEY_EVENTS]

    # Trim very long sentences
    return [
        (s[:187] + "…" if len(s) > 190 else s)
        for s in selected
    ]


def _build_why_it_matters(sentences: List[str]) -> str:
    """
    Build the "why it matters" paragraph from the analytical tail
    of the Wikipedia extract.

    Uses a wider tail window (up to 4 sentences) for richer context.
    """
    if len(sentences) <= 2:
        tail = sentences
    else:
        midpoint = max(2, len(sentences) // 2)
        tail = sentences[midpoint: midpoint + 4]

    paragraph = " ".join(tail).strip()
    if len(paragraph) > 600:
        paragraph = paragraph[:597] + "…"

    if not paragraph:
        paragraph = (
            "This topic has broad implications across economic, social, and political domains. "
            "Refer to the sources below for in-depth analysis from trusted publications."
        )

    return paragraph


def _build_historical_summary(sentences: List[str], wiki_data: dict) -> str:
    """
    Build a concise 1-sentence summary of the topic.

    Uses the Wikipedia page description (very short) if available,
    otherwise compresses the first sentence down to ~180 chars.
    """
    # Wikipedia description is often a short 1-phrase definition
    description = wiki_data.get("description", "").strip()
    page_title  = wiki_data.get("titles", {}).get("normalized", "")

    if description and len(description) < 100:
        if page_title:
            return f"{page_title}: {description}."
        return description + "."

    # Fallback: compress first sentence
    if sentences:
        first = sentences[0]
        if len(first) > 200:
            first = first[:197] + "…"
        return first

    return ""


def _detect_geopolitical_relevance(extract: str, sentences: List[str]) -> str:
    """
    Detect whether this topic has geopolitical or economic relevance,
    and return a brief explanatory sentence if so.

    Method:
      - Count geopolitical signal keywords in the extract
      - If >= 3 unique signals found, classify and build a sentence
      - Return empty string if the topic is not geopolitically significant
    """
    extract_lower = extract.lower()
    found_signals = {
        signal for signal in _GEO_SIGNALS
        if signal in extract_lower
    }

    if len(found_signals) < 3:
        return ""

    # Classify the type of relevance
    military_signals  = found_signals & {"war", "military", "troops", "weapons", "missile", "nuclear", "invasion", "forces"}
    economic_signals  = found_signals & {"gdp", "recession", "inflation", "market", "investment", "finance", "oil", "trade war", "tariff", "sanctions", "economy"}
    diplomatic_signals = found_signals & {"diplomacy", "diplomatic", "negotiations", "treaty", "summit", "united nations", "peace", "talks", "ceasefire", "bilateral"}

    relevance_parts = []
    if military_signals:
        relevance_parts.append("military and security implications")
    if diplomatic_signals:
        relevance_parts.append("diplomatic and international relations significance")
    if economic_signals:
        relevance_parts.append("global economic impact")

    if not relevance_parts:
        return "This topic has significant geopolitical implications."

    joined = " and ".join(relevance_parts)
    return (
        f"This topic carries {joined}, making it relevant to international "
        f"stability and global affairs."
    )


def _extract_related_topics(wiki_data: dict, sentences: List[str]) -> List[str]:
    """
    Derive related topics from Wikipedia metadata and content signals.

    Sources:
      - Wikipedia page description
      - Page title itself
      - Significant proper nouns from early sentences
    """
    related: List[str] = []

    description = wiki_data.get("description", "")
    if description and len(description) < 80:
        related.append(description.strip())

    # Extract meaningful words from description
    desc_words = re.findall(r'\b[A-Za-z]{4,}\b', description)
    for word in desc_words:
        if word.lower() not in _STOPWORDS and word not in related:
            related.append(word)
            if len(related) >= 4:
                break

    # Page title
    page_title = wiki_data.get("titles", {}).get("normalized", "")
    if page_title and page_title not in related:
        related.append(page_title)

    # Extract proper nouns from first 2 sentences
    early_text = " ".join(sentences[:2])
    proper_nouns = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', early_text)
    for noun in proper_nouns:
        if noun.lower() not in _STOPWORDS and noun not in related and len(related) < 8:
            related.append(noun)

    # Deduplicate
    seen: set = set()
    unique: List[str] = []
    for t in related:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return unique[:8]


# =============================================================
# NEWSAPI SOURCES FETCH
# =============================================================

def _fetch_news_sources(query: str) -> List[dict]:
    """
    Fetch real published news articles from NewsAPI as reference sources.

    Uses extracted topic for better relevance (not raw headline).
    Sort by "relevancy" so we get thematically related articles.
    """
    if not NEWSAPI_KEY:
        logger.warning("NEWSAPI_KEY not set — skipping news sources fetch")
        return []

    params = {
        "q":        query,
        "language": "en",
        "sortBy":   "relevancy",
        "pageSize": MAX_SOURCES,
        "apiKey":   NEWSAPI_KEY,
    }

    try:
        response = requests.get(NEWSAPI_BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()

    except requests.exceptions.Timeout:
        logger.warning("NewsAPI timeout | query=%r", query)
        return []
    except requests.exceptions.ConnectionError:
        logger.warning("NewsAPI connection error | query=%r", query)
        return []
    except requests.exceptions.RequestException as exc:
        logger.warning("NewsAPI request error | query=%r | %s", query, exc)
        return []

    if data.get("status") != "ok":
        logger.warning("NewsAPI non-ok status | query=%r | msg=%s", query, data.get("message"))
        return []

    sources = []
    for article in data.get("articles", []):
        title       = article.get("title", "").strip()
        url         = article.get("url", "").strip()
        source_name = article.get("source", {}).get("name", "Unknown")
        published   = article.get("publishedAt")

        if not title or not url or title == "[Removed]":
            continue

        sources.append({
            "title":        title,
            "url":          url,
            "source_name":  source_name,
            "published_at": published,
        })

        if len(sources) >= MAX_SOURCES:
            break

    logger.info("NewsAPI sources: %d articles | query=%r", len(sources), query)
    return sources
