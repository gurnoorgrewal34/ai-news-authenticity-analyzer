# =============================================================
# Frontend/app.py — AI News Authenticity & Mental Wellness Analyzer
#
# FLOW:
#   1. User types a keyword  (e.g. "gold prices")
#   2. We call GET /news/?keyword=...  → shows article cards
#   3. Each card has an "Analyze" button
#   4. Clicking Analyze sends POST /analyze/ with that article's
#      title + description → shows full wellness analysis
#
# HOW TO RUN (from project root):
#   streamlit run Frontend/app.py
#   (FastAPI backend must be running in another terminal)
# =============================================================

import streamlit as st    # Python web-app framework — no HTML needed
import requests           # For calling our FastAPI backend
import time               # For brief sleep to smooth transitions


# =============================================================
# PAGE CONFIG — must be the VERY FIRST Streamlit call
# =============================================================
st.set_page_config(
    page_title="AI News Analyzer",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =============================================================
# GLOBAL CSS
#
# Streamlit lets us inject CSS via st.markdown(unsafe_allow_html=True).
# Everything here is scoped to our dark theme.
# =============================================================
st.markdown("""
<style>
    /* ---------- Global ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0d0f1a; }

    /* Hide Streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* ---------- Hero header ---------- */
    .hero-title {
        text-align: center;
        font-size: 2.7rem;
        font-weight: 800;
        background: linear-gradient(135deg, #818cf8 0%, #a78bfa 50%, #e879f9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.2;
        padding: 1.2rem 0 0.4rem;
    }
    .hero-sub {
        text-align: center;
        color: #64748b;
        font-size: 1.05rem;
        margin-bottom: 2.4rem;
    }

    /* ---------- Search bar wrapper ---------- */
    .search-wrap {
        background: #13162b;
        border: 1px solid #1e2340;
        border-radius: 16px;
        padding: 1.4rem 1.8rem 1.6rem;
        margin-bottom: 2rem;
    }

    /* ---------- Article card ---------- */
    .article-card {
        background: #13162b;
        border: 1px solid #1e2340;
        border-radius: 16px;
        padding: 1.4rem 1.6rem 1.2rem;
        margin-bottom: 1.2rem;
        transition: border-color 0.2s;
    }
    .article-card:hover { border-color: #6366f1; }

    .article-source-date {
        display: flex;
        gap: 0.8rem;
        align-items: center;
        margin-bottom: 0.55rem;
    }
    .pill {
        display: inline-block;
        background: #1e2340;
        color: #818cf8;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        letter-spacing: 0.04em;
    }
    .article-date { color: #475569; font-size: 0.78rem; }
    .article-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e2e8f0;
        margin: 0.3rem 0 0.5rem;
        line-height: 1.4;
    }
    .article-desc {
        color: #94a3b8;
        font-size: 0.88rem;
        line-height: 1.6;
        margin-bottom: 0.9rem;
    }
    .article-link a {
        color: #818cf8;
        font-size: 0.82rem;
        text-decoration: none;
        font-weight: 500;
    }
    .article-link a:hover { text-decoration: underline; }

    /* ---------- Results panel ---------- */
    .result-panel {
        background: #13162b;
        border: 1px solid #1e2340;
        border-radius: 16px;
        padding: 1.6rem 1.8rem;
        margin-top: 0.5rem;
        margin-bottom: 1.5rem;
    }
    .result-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #475569;
        margin-bottom: 0.4rem;
    }

    /* ---------- Sentiment badge ---------- */
    .badge {
        display: inline-block;
        padding: 0.32rem 1.1rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 0.95rem;
        letter-spacing: 0.04em;
    }
    .badge-POSITIVE { background:#052e16; color:#4ade80; border:1px solid #4ade80; }
    .badge-NEGATIVE { background:#2d0a0a; color:#f87171; border:1px solid #f87171; }
    .badge-NEUTRAL  { background:#0c1a2e; color:#60a5fa; border:1px solid #60a5fa; }

    /* ---------- Score bar ---------- */
    .bar-bg {
        background: #1e2340;
        border-radius: 999px;
        height: 8px;
        overflow: hidden;
        margin-top: 5px;
    }
    .bar-fill { height: 8px; border-radius: 999px; }

    /* ---------- Wellness impact chip ---------- */
    .impact-LOW      { color: #4ade80; font-size:1.5rem; font-weight:800; }
    .impact-MODERATE { color: #facc15; font-size:1.5rem; font-weight:800; }
    .impact-HIGH     { color: #f87171; font-size:1.5rem; font-weight:800; }

    /* ---------- Divider ---------- */
    .my-divider { border:none; border-top:1px solid #1e2340; margin:1.2rem 0; }

    /* ---------- Button overrides ---------- */
    .stButton > button {
        background: linear-gradient(135deg,#6366f1,#a855f7);
        color: #fff;
        border: none;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.92rem;
        padding: 0.55rem 1.4rem;
        transition: opacity 0.2s;
        width: 100%;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* Search button wider */
    div[data-testid="column"]:last-child .stButton > button {
        padding: 0.65rem 2rem;
        font-size: 1rem;
    }

    /* ---------- Input labels ---------- */
    .stTextInput label { color: #94a3b8 !important; font-weight: 600; font-size: 0.88rem; }

    /* ---------- st.metric overrides ---------- */
    [data-testid="metric-container"] {
        background: #1a1d2e;
        border: 1px solid #1e2340;
        border-radius: 12px;
        padding: 0.8rem 1rem;
    }
    [data-testid="stMetricValue"] { color: #e2e8f0 !important; font-weight: 800; }
    [data-testid="stMetricLabel"] { color: #64748b !important; font-size: 0.78rem !important; }

    /* ---------- Historical Context Panel ---------- */
    .ctx-panel {
        background: #0e1020;
        border: 1px solid #2a2f52;
        border-radius: 16px;
        padding: 1.5rem 1.8rem;
        margin-top: 0.8rem;
    }
    .ctx-section-title {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #475569;
        margin-bottom: 0.5rem;
    }
    .ctx-intro-box {
        background: #13162b;
        border-left: 3px solid #818cf8;
        border-radius: 0 10px 10px 0;
        padding: 0.9rem 1.1rem;
        color: #cbd5e1;
        font-size: 0.91rem;
        line-height: 1.75;
        margin-bottom: 0.2rem;
    }
    /* Timeline */
    .timeline-track {
        display: flex;
        gap: 0.75rem;
        overflow-x: auto;
        padding-bottom: 0.4rem;
        margin-bottom: 0.2rem;
        scrollbar-width: thin;
        scrollbar-color: #2a2f52 transparent;
    }
    .timeline-card {
        min-width: 170px;
        max-width: 200px;
        background: #13162b;
        border: 1px solid #2a2f52;
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        flex-shrink: 0;
    }
    .timeline-year {
        font-size: 1.1rem;
        font-weight: 800;
        color: #818cf8;
        margin-bottom: 0.3rem;
    }
    .timeline-event {
        font-size: 0.78rem;
        color: #94a3b8;
        line-height: 1.55;
    }
    /* Key events */
    .event-list li {
        color: #cbd5e1;
        font-size: 0.88rem;
        line-height: 1.7;
        margin-bottom: 0.35rem;
    }
    /* Why it matters */
    .why-box {
        background: #13162b;
        border: 1px solid #2a2f52;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        color: #94a3b8;
        font-size: 0.91rem;
        line-height: 1.75;
    }
    /* Related topic pills */
    .topic-tag {
        display: inline-block;
        background: #1a1d30;
        border: 1px solid #3730a3;
        color: #818cf8;
        font-size: 0.76rem;
        font-weight: 600;
        padding: 0.2rem 0.75rem;
        border-radius: 999px;
        margin: 0.2rem 0.2rem 0.2rem 0;
    }
    /* Source reference cards */
    .src-card {
        background: #13162b;
        border: 1px solid #1e2340;
        border-radius: 10px;
        padding: 0.65rem 0.9rem;
        margin-bottom: 0.5rem;
    }
    .src-card a {
        color: #818cf8;
        font-size: 0.84rem;
        font-weight: 600;
        text-decoration: none;
    }
    .src-card a:hover { text-decoration: underline; }
    .src-meta { color: #475569; font-size: 0.75rem; margin-top: 0.15rem; }
</style>
""", unsafe_allow_html=True)


# =============================================================
# BACKEND URLS — change only here if the server moves
# =============================================================
NEWS_URL    = "http://127.0.0.1:8000/news/"
ANALYZE_URL = "http://127.0.0.1:8000/analyze/"
CONTEXT_URL = "http://127.0.0.1:8000/context/"   # Module 4: Historical context


# =============================================================
# UTILITY HELPERS
# =============================================================

def score_color(score: float) -> str:
    """Return a hex color: green for low, yellow for mid, red for high."""
    if score < 0.35:
        return "#4ade80"
    elif score < 0.65:
        return "#facc15"
    return "#f87171"


def render_bar(score: float):
    """Render a slim colored progress bar for a 0–1 score."""
    color   = score_color(score)
    percent = int(score * 100)
    st.markdown(f"""
    <div class="bar-bg">
        <div class="bar-fill" style="width:{percent}%; background:{color};"></div>
    </div>
    """, unsafe_allow_html=True)


def fmt_date(iso: str | None) -> str:
    """
    Convert an ISO 8601 timestamp like '2026-05-16T08:00:00Z'
    into a readable string like 'May 16, 2026'.
    Returns '—' if the value is missing or unparseable.
    """
    if not iso:
        return "—"
    try:
        from datetime import datetime, timezone
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return dt.strftime("%b %d, %Y")
    except Exception:
        # If the date format is unexpected, just return the raw string
        return iso[:10] if len(iso) >= 10 else iso


# =============================================================
# HERO HEADER
# =============================================================
st.markdown('<h1 class="hero-title">🧠 AI News Authenticity & Mental Wellness Analyzer</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Search live news → pick an article → get AI sentiment, '
    'fear scoring, and mental wellness analysis in seconds.</p>',
    unsafe_allow_html=True,
)


# =============================================================
# SESSION STATE INITIALISATION
#
# st.session_state persists values between Streamlit reruns.
# Every time the user clicks a button, Streamlit reruns the
# entire script — session_state is how we "remember" things.
# =============================================================
if "articles"         not in st.session_state:
    st.session_state.articles         = []    # List of fetched news articles
if "search_done"      not in st.session_state:
    st.session_state.search_done      = False # Has the user searched yet?
if "analysis_result"  not in st.session_state:
    st.session_state.analysis_result  = None  # Last analysis JSON response
if "analyzed_index"   not in st.session_state:
    st.session_state.analyzed_index   = None  # Which card's Analyze was clicked
if "search_keyword"   not in st.session_state:
    st.session_state.search_keyword   = ""    # Last searched keyword
if "news_error"       not in st.session_state:
    st.session_state.news_error       = None  # Error message from /news call
if "analyze_error"    not in st.session_state:
    st.session_state.analyze_error    = None  # Error message from /analyze call
if "context_result"   not in st.session_state:
    st.session_state.context_result   = None  # Last context JSON response (Module 4)
if "context_error"    not in st.session_state:
    st.session_state.context_error    = None  # Error message from /context call


# =============================================================
# SEARCH SECTION
# =============================================================
st.markdown('<div class="search-wrap">', unsafe_allow_html=True)

# Two-column layout: wide text input | narrower button
search_col, btn_col = st.columns([5, 1])

with search_col:
    keyword_input = st.text_input(
        label="🔍 Enter a news keyword",
        placeholder='e.g.  "gold prices"   "AI"   "climate"   "bitcoin"',
        value=st.session_state.search_keyword,
        key="keyword_box",
        label_visibility="collapsed",
    )

with btn_col:
    search_clicked = st.button("Search News", key="search_btn", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)   # close search-wrap


# =============================================================
# SEARCH LOGIC — fires when user clicks "Search News"
# =============================================================
if search_clicked:
    kw = keyword_input.strip()

    if len(kw) < 2:
        # Keyword too short — show warning and stop
        st.warning("⚠️ Please enter at least 2 characters.")
    else:
        # Reset any previous results
        st.session_state.articles        = []
        st.session_state.search_done     = False
        st.session_state.analysis_result = None
        st.session_state.analyzed_index  = None
        st.session_state.news_error      = None
        st.session_state.analyze_error   = None
        st.session_state.search_keyword  = kw

        # ---- Call the backend /news/ endpoint ----
        with st.spinner(f'Fetching live news for **"{kw}"**…'):
            try:
                resp = requests.get(
                    NEWS_URL,
                    params={"keyword": kw, "page_size": 10},
                    timeout=15,
                )
                resp.raise_for_status()
                data = resp.json()

                articles = data.get("articles", [])

                # Filter out articles that have no title or description
                # (NewsAPI sometimes returns incomplete entries)
                articles = [
                    a for a in articles
                    if a.get("title") and a.get("description")
                    and a["title"] != "[Removed]"
                ]

                if articles:
                    st.session_state.articles    = articles
                    st.session_state.search_done = True
                else:
                    st.session_state.news_error = (
                        f"No articles found for **\"{kw}\"**. "
                        "Try a different keyword."
                    )

            except requests.exceptions.ConnectionError:
                st.session_state.news_error = (
                    "🔌 **Connection Error:** Cannot reach the backend.\n\n"
                    "Make sure FastAPI is running:\n"
                    "```\ncd Backend\npython -m uvicorn app.main:app --reload\n```"
                )
            except requests.exceptions.Timeout:
                st.session_state.news_error = (
                    "⏱️ **Timeout:** The backend took too long. Please try again."
                )
            except requests.exceptions.HTTPError as e:
                code = e.response.status_code if e.response else "?"
                st.session_state.news_error = (
                    f"⚠️ **HTTP {code}:** {e}"
                )
            except Exception as e:
                st.session_state.news_error = f"❓ Unexpected error: `{e}`"


# =============================================================
# DISPLAY NEWS ERROR (if search failed)
# =============================================================
if st.session_state.news_error:
    st.error(st.session_state.news_error)


# =============================================================
# ARTICLE CARDS — shown after a successful search
# =============================================================
if st.session_state.search_done and st.session_state.articles:

    keyword = st.session_state.search_keyword
    count   = len(st.session_state.articles)

    st.markdown(
        f'<p style="color:#64748b; font-size:0.9rem; margin-bottom:1rem;">'
        f'Showing <strong style="color:#818cf8">{count} articles</strong> '
        f'for <strong style="color:#e2e8f0">"{keyword}"</strong></p>',
        unsafe_allow_html=True,
    )

    # ----------------------------------------------------------
    # Render one card per article
    # ----------------------------------------------------------
    for idx, article in enumerate(st.session_state.articles):

        title       = article.get("title",       "No title")
        description = article.get("description", "No description available.")
        source      = article.get("source",      "Unknown source")
        url         = article.get("url",         "#")
        pub_date    = fmt_date(article.get("published_at"))

        # Truncate long descriptions for the card preview
        # (full description is still sent to the analyzer)
        desc_preview = (
            description[:220] + "…"
            if len(description) > 220
            else description
        )

        # ---- Article card HTML ----
        st.markdown(f"""
        <div class="article-card">
            <div class="article-source-date">
                <span class="pill">📰 {source}</span>
                <span class="article-date">🗓 {pub_date}</span>
            </div>
            <div class="article-title">{title}</div>
            <div class="article-desc">{desc_preview}</div>
            <div class="article-link">
                <a href="{url}" target="_blank" rel="noopener noreferrer">
                    🔗 Read full article ↗
                </a>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ---- Analyze button (one per card) ----
        # The key must be unique per card, so we use the index.
        analyze_btn = st.button(
            label=f"🔍 Analyze this article",
            key=f"analyze_{idx}",
            use_container_width=False,
        )

        # ---- When this card's Analyze button is clicked ----
        if analyze_btn:
            # Reset previous analysis (and context from prior card)
            st.session_state.analysis_result = None
            st.session_state.analyzed_index  = idx
            st.session_state.analyze_error   = None
            st.session_state.context_result  = None
            st.session_state.context_error   = None

            # Build the payload for POST /analyze/
            # We now include keyword and source so the backend
            # can store them in the SQLite history database.
            payload = {
                "title":       title,
                "description": description,          # Full text, not truncated preview
                "keyword":     st.session_state.search_keyword or None,
                "source":      source if source != "Unknown source" else None,
            }

            with st.spinner("🤖 Running AI analysis… Please wait."):
                try:
                    res = requests.post(
                        ANALYZE_URL,
                        json=payload,
                        timeout=30,
                    )
                    res.raise_for_status()

                    # Small pause so the spinner is visible
                    time.sleep(0.25)

                    # Store result in session_state so it survives the rerun
                    st.session_state.analysis_result = res.json()

                    # --------------------------------------------------
                    # Module 4: Fetch historical context immediately after
                    # analysis. This is a secondary, non-blocking call —
                    # if it fails, the main analysis result is unaffected.
                    # We use the article title as the topic query because
                    # it's the most descriptive, human-readable phrase.
                    # --------------------------------------------------
                    try:
                        ctx_res = requests.get(
                            CONTEXT_URL,
                            params={"topic": title},
                            timeout=15,
                        )
                        ctx_res.raise_for_status()
                        st.session_state.context_result = ctx_res.json()
                    except requests.exceptions.ConnectionError:
                        st.session_state.context_error = (
                            "🔌 Cannot reach backend for historical context."
                        )
                    except requests.exceptions.Timeout:
                        st.session_state.context_error = (
                            "⏱️ Historical context request timed out."
                        )
                    except Exception:
                        # Context failure must never crash the main analysis
                        st.session_state.context_error = (
                            "Historical context unavailable for this topic."
                        )

                except requests.exceptions.ConnectionError:
                    st.session_state.analyze_error = (
                        "🔌 **Connection Error:** Backend is unreachable. "
                        "Make sure FastAPI is running."
                    )
                except requests.exceptions.Timeout:
                    st.session_state.analyze_error = (
                        "⏱️ **Timeout:** The AI model is taking too long. "
                        "It may still be loading — try again in a moment."
                    )
                except requests.exceptions.HTTPError as http_err:
                    code = http_err.response.status_code if http_err.response else "?"
                    if code == 422:
                        st.session_state.analyze_error = (
                            "📋 **Validation Error (422):** "
                            "The article text was rejected by the backend. "
                            "The title or description may be too short."
                        )
                    elif code == 503:
                        st.session_state.analyze_error = (
                            "🤖 **Model Unavailable (503):** "
                            "The AI sentiment model is not loaded. "
                            "Check the backend terminal for errors."
                        )
                    else:
                        st.session_state.analyze_error = (
                            f"⚠️ **HTTP {code}:** {http_err}"
                        )
                except Exception as unexpected:
                    st.session_state.analyze_error = (
                        f"❓ Unexpected error: `{unexpected}`"
                    )

            # Streamlit reruns automatically after a button click,
            # so the result panel below will render on the next pass.
            st.rerun()

        # ---- Show analysis result below the card that was analyzed ----
        if (
            st.session_state.analyzed_index == idx
            and st.session_state.analysis_result is not None
        ):
            # ---------------------------------------------------------
            # RESULTS PANEL (v3 — with AI Summary, Key Points, Emotional Label)
            # ---------------------------------------------------------
            data = st.session_state.analysis_result

            # ------ Unpack all nested fields from the API response ------
            sentiment = data.get("sentiment", {})
            wellness  = data.get("wellness_scores", {})
            summary   = data.get("summary", {})
            insights  = data.get("article_insights", {})   # NEW in v3

            label       = sentiment.get("label", "UNKNOWN")
            conf_pct    = sentiment.get("confidence_percent", "—")
            confidence  = sentiment.get("confidence", 0.0)

            fear_score      = wellness.get("fear_score", 0.0)
            clickbait_score = wellness.get("clickbait_score", 0.0)
            impact_level    = wellness.get("wellness_impact", "—")
            impact_msg      = wellness.get("wellness_message", "")

            intensity      = summary.get("emotional_intensity", "—")
            recommendation = summary.get("recommendation", "—")
            model_used     = data.get("model_used", "—")
            version        = data.get("analysis_version", "3.0")

            # NEW: Article Intelligence fields
            quick_summary        = insights.get("quick_summary", "")
            key_points           = insights.get("key_points", [])
            reading_time_label   = insights.get("reading_time_label", "—")
            emotional_label      = insights.get("emotional_label", label)
            emotional_desc       = insights.get("emotional_description", "")
            summarizer_used      = insights.get("summarizer_used", False)

            badge_cls   = f"badge-{label}" if label in ("POSITIVE","NEGATIVE","NEUTRAL") else "badge-NEUTRAL"

            st.markdown('<div class="result-panel">', unsafe_allow_html=True)

            # ------ Panel header with reading time ------
            summarizer_note = "AI summarized" if summarizer_used else "extractive fallback"
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1.2rem;">'
                f'  <span style="color:#818cf8; font-weight:700; font-size:1rem;">📊 Analysis Results'
                f'    <span style="color:#475569; font-size:0.78rem; font-weight:400;"> · v{version} · {model_used}</span>'
                f'  </span>'
                f'  <span style="background:#1e2340; color:#94a3b8; font-size:0.78rem; '
                f'    padding:0.25rem 0.8rem; border-radius:999px; font-weight:600;">'
                f'    ⏱ {reading_time_label}'
                f'  </span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # ============================================================
            # SECTION A: Emotional Tone (the human-friendly hero element)
            # This replaces the raw POSITIVE/NEGATIVE label as the first
            # thing users see — much easier to understand at a glance.
            # ============================================================
            st.markdown('<div class="result-section-title">🎭 Emotional Tone</div>', unsafe_allow_html=True)
            st.markdown(
                f'<p style="font-size:1.2rem; font-weight:800; color:#e2e8f0; margin:0.2rem 0 0.3rem;">'
                f'{emotional_label}</p>'
                f'<p style="color:#94a3b8; font-size:0.88rem; line-height:1.6; margin:0 0 0.5rem;">'
                f'{emotional_desc}</p>',
                unsafe_allow_html=True,
            )
            # Show the raw badge as a small secondary label
            st.markdown(
                f'<span class="badge {badge_cls}" style="font-size:0.75rem; padding:0.2rem 0.7rem;">'
                f'{label} · {conf_pct} confidence</span>',
                unsafe_allow_html=True,
            )

            st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

            # ============================================================
            # SECTION B: Quick Summary
            # AI-generated (DistilBART) or first-2-sentences fallback.
            # ============================================================
            if quick_summary:
                src_note = "🤖 AI-generated summary" if summarizer_used else "📄 Extracted from article"
                st.markdown('<div class="result-section-title">📝 Quick Summary</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="background:#0d0f1a; border-left:3px solid #6366f1; '
                    f'padding:0.9rem 1.1rem; border-radius:0 10px 10px 0; margin-bottom:0.4rem;">'
                    f'<p style="color:#cbd5e1; font-size:0.92rem; line-height:1.75; margin:0;">'
                    f'{quick_summary}</p>'
                    f'</div>'
                    f'<p style="color:#475569; font-size:0.75rem; margin-top:0.3rem;">{src_note}</p>',
                    unsafe_allow_html=True,
                )
                st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

            # ============================================================
            # SECTION C: Key Points
            # Extracted using position + content heuristics (no extra model).
            # ============================================================
            if key_points:
                st.markdown('<div class="result-section-title">🔑 Key Points</div>', unsafe_allow_html=True)
                # Build bullet list as HTML for consistent dark-theme styling
                bullets_html = "".join(
                    f'<li style="color:#cbd5e1; font-size:0.9rem; line-height:1.7; margin-bottom:0.3rem;">'
                    f'{pt}</li>'
                    for pt in key_points
                )
                st.markdown(
                    f'<ul style="padding-left:1.2rem; margin:0.4rem 0 0;">{bullets_html}</ul>',
                    unsafe_allow_html=True,
                )
                st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

            # ============================================================
            # SECTION D: Scores — Fear · Clickbait (side by side)
            # ============================================================
            r2a, r2b = st.columns(2)

            with r2a:
                fc = score_color(fear_score)
                st.markdown('<div class="result-section-title">😨 Fear Score</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<span style="font-size:1.5rem; font-weight:800; color:{fc};">'
                    f'{fear_score:.2f} / 1.00</span>',
                    unsafe_allow_html=True,
                )
                render_bar(fear_score)
                st.caption("Alarm/fear keyword density")

            with r2b:
                cc = score_color(clickbait_score)
                st.markdown('<div class="result-section-title">🎣 Clickbait Score</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<span style="font-size:1.5rem; font-weight:800; color:{cc};">'
                    f'{clickbait_score:.2f} / 1.00</span>',
                    unsafe_allow_html=True,
                )
                render_bar(clickbait_score)
                st.caption("Sensational language in headline")

            st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

            # ============================================================
            # SECTION E: Wellness Impact
            # ============================================================
            impact_colors = {"LOW":"#4ade80","MODERATE":"#facc15","HIGH":"#f87171"}

            st.markdown('<div class="result-section-title">🧘 Mental Wellness Impact</div>', unsafe_allow_html=True)
            st.markdown(
                f'<span class="impact-{impact_level.upper()}">{impact_level}</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<p style="color:#94a3b8; font-size:0.9rem; line-height:1.65; margin-top:0.5rem;">'
                f'{impact_msg}</p>',
                unsafe_allow_html=True,
            )

            st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

            # ============================================================
            # SECTION F: Recommendation
            # ============================================================
            st.markdown('<div class="result-section-title">💡 Wellness Insight</div>', unsafe_allow_html=True)
            st.markdown(
                f'<p style="color:#cbd5e1; font-size:0.93rem; line-height:1.7; margin-top:0.3rem;">'
                f'{recommendation}</p>',
                unsafe_allow_html=True,
            )

            st.markdown('</div>', unsafe_allow_html=True)   # close result-panel

            # ============================================================
            # SECTION G: Historical Context & Background  (Module 4)
            #
            # A separate expandable panel populated by GET /context.
            # Non-blocking: if context fetch failed, shows a clean
            # warning without disrupting the main analysis above.
            # ============================================================
            with st.expander("🌍 Historical Context & Background", expanded=True):

                ctx     = st.session_state.context_result
                ctx_err = st.session_state.context_error

                if ctx_err and ctx is None:
                    st.warning(f"⚠️ {ctx_err}")

                elif ctx is None:
                    st.info("🔄 Historical context is loading or unavailable for this topic.")

                else:
                    hist_ctx   = ctx.get("historical_context", "")
                    timeline   = ctx.get("timeline_points",    [])
                    key_events = ctx.get("key_events",         [])
                    why        = ctx.get("why_it_matters",     "")
                    rel_topics = ctx.get("related_topics",     [])
                    sources    = ctx.get("sources",            [])
                    wiki_url   = ctx.get("wikipedia_url")
                    freshness  = ctx.get("data_freshness",     "")

                    st.markdown('<div class="ctx-panel">', unsafe_allow_html=True)

                    # Header row: title + Wikipedia source link
                    wiki_badge = (
                        f'<a href="{wiki_url}" target="_blank" '
                        f'style="color:#818cf8;font-size:0.75rem;font-weight:600;'
                        f'text-decoration:none;">🔗 Wikipedia source ↗</a>'
                        if wiki_url else ""
                    )
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;'
                        f'align-items:center;margin-bottom:1.2rem;">'
                        f'  <span style="color:#818cf8;font-weight:700;font-size:1rem;">'
                        f'    📚 Historical Background'
                        f'    <span style="color:#475569;font-size:0.77rem;font-weight:400;">'
                        f'    · Wikipedia + NewsAPI · zero hallucinations</span>'
                        f'  </span>'
                        f'  {wiki_badge}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                    # ---- A: Historical Context intro ----
                    if hist_ctx:
                        st.markdown(
                            '<div class="ctx-section-title">📜 Historical Context</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="ctx-intro-box">{hist_ctx}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

                    # ---- B: Timeline cards ----
                    if timeline:
                        st.markdown(
                            '<div class="ctx-section-title">📅 Timeline of Key Moments</div>',
                            unsafe_allow_html=True,
                        )
                        cards_html = "".join(
                            f'<div class="timeline-card">'
                            f'  <div class="timeline-year">{pt["year"]}</div>'
                            f'  <div class="timeline-event">{pt["event"]}</div>'
                            f'</div>'
                            for pt in timeline
                        )
                        st.markdown(
                            f'<div class="timeline-track">{cards_html}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

                    # ---- C: Key Events bullets ----
                    if key_events:
                        st.markdown(
                            '<div class="ctx-section-title">⚡ Key Historical Events</div>',
                            unsafe_allow_html=True,
                        )
                        bullets = "".join(f'<li>{ev}</li>' for ev in key_events)
                        st.markdown(
                            f'<ul class="event-list" style="padding-left:1.2rem;margin:0.4rem 0;">'
                            f'{bullets}</ul>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

                    # ---- D: Why It Matters ----
                    if why:
                        st.markdown(
                            '<div class="ctx-section-title">🌐 Why This Matters</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<div class="why-box">{why}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

                    # ---- E: Related Topics pills ----
                    if rel_topics:
                        st.markdown(
                            '<div class="ctx-section-title">🏷️ Related Topics</div>',
                            unsafe_allow_html=True,
                        )
                        tags = "".join(
                            f'<span class="topic-tag">{t}</span>' for t in rel_topics
                        )
                        st.markdown(
                            f'<div style="margin:0.4rem 0 0.6rem;">{tags}</div>',
                            unsafe_allow_html=True,
                        )
                        st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

                    # ---- F: Reliable Source References ----
                    if sources:
                        st.markdown(
                            '<div class="ctx-section-title">🔗 Reliable References</div>',
                            unsafe_allow_html=True,
                        )
                        for src in sources:
                            s_title = src.get("title",       "Article")
                            s_url   = src.get("url",          "#")
                            s_name  = src.get("source_name", "Unknown source")
                            s_pub   = src.get("published_at", "")
                            s_date  = fmt_date(s_pub) if s_pub else "—"
                            st.markdown(
                                f'<div class="src-card">'
                                f'  <a href="{s_url}" target="_blank" rel="noopener noreferrer">'
                                f'    {s_title}'
                                f'  </a>'
                                f'  <div class="src-meta">📰 {s_name} &nbsp;·&nbsp; 🗓 {s_date}</div>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

                    elif not hist_ctx:
                        # Nothing came back at all
                        st.info(
                            "💭 No historical data found for this specific topic. "
                            "Try a broader keyword (e.g. 'gold', 'AI', 'climate change')."
                        )

                    # Data freshness footnote
                    if freshness:
                        try:
                            from datetime import datetime as _dt
                            ft = _dt.strptime(freshness, "%Y-%m-%dT%H:%M:%SZ")
                            freshness_fmt = ft.strftime("Data fetched at %H:%M UTC on %b %d, %Y")
                        except Exception:
                            freshness_fmt = f"Data fetched: {freshness}"
                        st.markdown(
                            f'<p style="color:#334155;font-size:0.72rem;'
                            f'margin-top:0.8rem;text-align:right;">{freshness_fmt}</p>',
                            unsafe_allow_html=True,
                        )

                    st.markdown('</div>', unsafe_allow_html=True)  # close ctx-panel

            # Collapsible raw JSON for debugging / developer view
            with st.expander("🔍 Raw API response (developer view)"):
                st.json(data)

        # ---- Show analyze error below the relevant card ----
        if (
            st.session_state.analyzed_index == idx
            and st.session_state.analyze_error is not None
        ):
            st.error(st.session_state.analyze_error)

        # Visual separator between cards (not after the last one)
        if idx < len(st.session_state.articles) - 1:
            st.markdown('<hr class="my-divider">', unsafe_allow_html=True)


# =============================================================
# EMPTY STATE — shown before the first search
# =============================================================
if not st.session_state.search_done and not st.session_state.news_error:
    st.markdown("""
    <div style="text-align:center; padding:3rem 0; color:#334155;">
        <div style="font-size:3.5rem; margin-bottom:1rem;">🔎</div>
        <p style="font-size:1.05rem; color:#475569;">
            Enter a keyword above and click <strong style="color:#818cf8">Search News</strong>
            to fetch live articles.
        </p>
        <p style="font-size:0.85rem; color:#334155; margin-top:0.4rem;">
            Try: <em>gold prices · AI · bitcoin · climate · elections</em>
        </p>
    </div>
    """, unsafe_allow_html=True)


# =============================================================
# HISTORY SECTION
#
# Shows past analysis records stored in the SQLite database.
# Displayed in a collapsible section so it doesn't clutter
# the main search flow.
# =============================================================
HISTORY_URL = "http://127.0.0.1:8000/history/"

st.markdown('<hr class="my-divider">', unsafe_allow_html=True)

# st.expander() creates a collapsible section — click to open/close
with st.expander("🗂️ View Analysis History (SQLite database)", expanded=False):

    # Controls row: limit selector + refresh button
    hist_col1, hist_col2, _ = st.columns([1, 1, 4])

    with hist_col1:
        # Dropdown to choose how many records to show
        hist_limit = st.selectbox(
            "Show records",
            options=[10, 25, 50, 100],
            index=0,
            key="hist_limit",
            label_visibility="collapsed",
        )

    with hist_col2:
        refresh_history = st.button("🔄 Load History", key="refresh_history")

    # ---- Fetch history when the button is clicked ----
    if refresh_history or st.session_state.get("history_loaded"):
        with st.spinner("Loading history from database…"):
            try:
                hist_resp = requests.get(
                    HISTORY_URL,
                    params={"limit": hist_limit, "offset": 0},
                    timeout=10,
                )
                hist_resp.raise_for_status()
                hist_data   = hist_resp.json()
                records     = hist_data.get("records", [])
                total       = hist_data.get("total_records", 0)

                # Mark that history has been loaded (persists across reruns)
                st.session_state["history_loaded"] = True

                if not records:
                    st.info(
                        "📭 No analysis history yet. "
                        "Search for news articles and click Analyze to start building history."
                    )
                else:
                    st.markdown(
                        f'<p style="color:#64748b; font-size:0.85rem; margin-bottom:0.8rem;">'
                        f'Showing <strong style="color:#818cf8">{len(records)}</strong> of '
                        f'<strong style="color:#e2e8f0">{total}</strong> total records '
                        f'(newest first)</p>',
                        unsafe_allow_html=True,
                    )

                    # ---- Render each record as a compact row ----
                    for rec in records:
                        # Sentiment color
                        sent       = rec.get("sentiment", "NEUTRAL")
                        sent_color = {"POSITIVE":"#4ade80","NEGATIVE":"#f87171","NEUTRAL":"#60a5fa"}.get(sent, "#94a3b8")

                        # Wellness impact color
                        impact     = rec.get("wellness_impact", "LOW")
                        imp_color  = {"LOW":"#4ade80","MODERATE":"#facc15","HIGH":"#f87171"}.get(impact, "#94a3b8")

                        # Format the timestamp nicely
                        raw_ts = rec.get("analyzed_at", "")
                        try:
                            from datetime import datetime
                            ts = datetime.fromisoformat(raw_ts).strftime("%b %d, %Y %H:%M")
                        except Exception:
                            ts = raw_ts[:16] if raw_ts else "—"

                        # Title (truncated if long)
                        rec_title  = rec.get("title", "Untitled")
                        title_disp = rec_title[:80] + "…" if len(rec_title) > 80 else rec_title

                        keyword_disp = rec.get("keyword") or "—"
                        source_disp  = rec.get("source")  or "—"
                        em_label     = rec.get("emotional_label") or sent
                        confidence   = rec.get("confidence", 0)
                        fear_sc      = rec.get("fear_score", 0)

                        # Render as a compact styled card
                        st.markdown(f"""
                        <div style="background:#13162b; border:1px solid #1e2340;
                                    border-radius:12px; padding:0.85rem 1.1rem;
                                    margin-bottom:0.6rem;">
                            <div style="display:flex; justify-content:space-between;
                                        align-items:flex-start; flex-wrap:wrap; gap:0.4rem;">
                                <div style="flex:1; min-width:200px;">
                                    <p style="color:#e2e8f0; font-size:0.88rem; font-weight:600;
                                               margin:0 0 0.25rem;">{title_disp}</p>
                                    <p style="color:#475569; font-size:0.75rem; margin:0;">
                                        🔍 {keyword_disp} &nbsp;·&nbsp; 📰 {source_disp}
                                        &nbsp;·&nbsp; 🗓 {ts}
                                    </p>
                                </div>
                                <div style="display:flex; gap:0.5rem; flex-wrap:wrap;
                                            align-items:center; margin-top:0.1rem;">
                                    <span style="background:#0d0f1a; color:{sent_color};
                                                 border:1px solid {sent_color};
                                                 border-radius:999px; font-size:0.72rem;
                                                 font-weight:700; padding:0.15rem 0.65rem;">
                                        {sent}
                                    </span>
                                    <span style="background:#0d0f1a; color:{imp_color};
                                                 border:1px solid {imp_color};
                                                 border-radius:999px; font-size:0.72rem;
                                                 font-weight:700; padding:0.15rem 0.65rem;">
                                        {impact}
                                    </span>
                                    <span style="color:#64748b; font-size:0.72rem;">
                                        {confidence*100:.0f}% conf &nbsp;·&nbsp; fear {fear_sc:.2f}
                                    </span>
                                </div>
                            </div>
                            <p style="color:#6366f1; font-size:0.75rem; margin:0.4rem 0 0;">
                                {em_label}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

            except requests.exceptions.ConnectionError:
                st.error("🔌 Cannot reach backend. Make sure FastAPI is running.")
            except requests.exceptions.Timeout:
                st.warning("⏱️ History request timed out. Try again.")
            except Exception as e:
                st.error(f"❓ Error loading history: `{e}`")

    else:
        # Shown before the user clicks Load History
        st.markdown(
            '<p style="color:#475569; font-size:0.88rem;">'
            'Click <strong>🔄 Load History</strong> to view past analyses from the database.'
            '</p>',
            unsafe_allow_html=True,
        )


# =============================================================
# SIDEBAR — backend status + guide
# =============================================================
with st.sidebar:
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Powered by:**
    - 🤗 DistilBERT SST-2 (sentiment)
    - 📝 DistilBART CNN (AI summarization)
    - 📰 NewsAPI (live headlines)
    - 📊 Finance override (rule-based)
    - 🧘 Wellness impact scoring
    - 🔑 Extractive key points
    """)

    st.markdown("---")
    st.markdown("### 🔗 Backend Status")

    try:
        ping = requests.get("http://127.0.0.1:8000/", timeout=2)
        if ping.status_code == 200:
            st.success("🟢 Backend online")
        else:
            st.warning(f"🟡 Status {ping.status_code}")
    except Exception:
        st.error("🔴 Backend offline")
        st.caption("Run: `uvicorn app.main:app --reload`")

    st.markdown("---")
    st.markdown("### 📊 Score Guide")
    st.markdown("""
    | Score | Level |
    |---|---|
    | 0.00 – 0.34 | 🟢 Low |
    | 0.35 – 0.64 | 🟡 Moderate |
    | 0.65 – 1.00 | 🔴 High |
    """)
    st.markdown("---")
    st.caption("FastAPI + HuggingFace + Streamlit")
