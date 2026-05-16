# AI News Authenticity & Mental Wellness Analyzer

## Project Overview

This project is a FastAPI backend that:

1. Fetches live news using NewsAPI
2. Analyzes emotional tone of news articles
3. Detects fear-heavy and clickbait-style content
4. Returns wellness-related insights

---

# Module 1 — News Fetching

Endpoint:

GET /news?keyword=AI

Flow:

User Request
    ↓
FastAPI Backend
    ↓
NewsAPI Request
    ↓
Receive Articles
    ↓
Return JSON Response

Technologies Used:
- FastAPI
- Requests
- NewsAPI
- Environment Variables

---

# Module 2 — News Analysis

Endpoint:

POST /analyze

Flow:

User sends title + description
        ↓
DistilBERT AI model reads text
        ↓
Sentiment analysis performed
        ↓
Fear score calculated
        ↓
Clickbait score calculated
        ↓
Wellness impact generated
        ↓
JSON response returned

Technologies Used:
- HuggingFace Transformers
- DistilBERT
- FastAPI
- Pydantic

---

# AI Model Used

Model:
distilbert-base-uncased-finetuned-sst-2-english

Purpose:
Detect emotional tone of text.

Possible outputs:
- POSITIVE
- NEGATIVE
- NEUTRAL

---

# Current Limitations

This system analyzes emotional tone,
NOT factual truth verification.

It cannot fully detect fake news.

It works best as a:
Mental Wellness & Emotional News Analysis System.

---

# Future Improvements

- Real fake-news detection
- Source credibility scoring
- Fact-checking integration
- Frontend dashboard
- Database storage
- User authentication