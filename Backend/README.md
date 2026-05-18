# 🗞️ Module 1: News Fetching System

**Part of:** AI News Authenticity & Mental Wellness Analyzer  
**Tech stack:** FastAPI · Python · NewsAPI · python-dotenv

---

## 📁 Folder Structure

```
Backend/
│
├── main.py                  ← App entry point — starts the server
│
├── .env                     ← 🔐 Secret keys (NEVER upload to GitHub)
├── .gitignore               ← Tells Git to ignore .env and other files
├── requirements.txt         ← All Python packages to install
│
└── app/                     ← Main application package
    ├── __init__.py          ← Marks 'app' as a Python package (leave empty)
    ├── config.py            ← Central configuration & settings
    │
    └── routers/             ← Route handlers (one file per topic)
        ├── __init__.py      ← Marks 'routers' as a Python package (leave empty)
        └── news.py          ← Handles the GET /news route
```

**Why this structure?**
- Each feature lives in its own file → easy to find and change
- `routers/` keeps routes organized as the project grows
- `config.py` is a single place for all settings
- `.env` keeps secrets out of your code

---

## 🚀 How to Run the Server

### Step 1 — Navigate to the Backend folder

```bash
cd api-news-analyzer/Backend
```

### Step 2 — Create a virtual environment (recommended)

```bash
# Create it
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Activate it (Mac/Linux)
source venv/bin/activate
```

> You'll see `(venv)` appear in your terminal — that's correct!

### Step 3 — Install all dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Add your NewsAPI key

1. Go to [https://newsapi.org/register](https://newsapi.org/register) → sign up for free
2. Copy your API key
3. Open the `.env` file and replace `YOUR_ACTUAL_KEY_HERE` with your key:

```
NEWSAPI_KEY=abc123youractualkey
```

### Step 5 — Start the server

```bash
uvicorn main:app --reload
```

- `main` → refers to `main.py`
- `app` → refers to the `app = FastAPI()` object inside main.py
- `--reload` → auto-restarts the server when you save changes

---

## ✅ Test the API

Once the server is running, open your browser:

| URL | What it does |
|-----|-------------|
| `http://127.0.0.1:8000/` | Welcome message |
| `http://127.0.0.1:8000/docs` | 🎯 Interactive API explorer (Swagger UI) |
| `http://127.0.0.1:8000/news?keyword=AI` | Fetch news about AI |
| `http://127.0.0.1:8000/news?keyword=Bitcoin` | Fetch news about Bitcoin |

### Example Response

```json
{
  "keyword": "AI",
  "total_results": 6821,
  "articles_shown": 10,
  "articles": [
    {
      "title": "Google launches new AI model",
      "description": "A breakthrough in artificial intelligence...",
      "source": "TechCrunch",
      "url": "https://techcrunch.com/...",
      "published_at": "2026-05-11T08:00:00Z"
    }
  ]
}
```

---

## 🔑 Environment Variables

| Variable | Description | Where to get it |
|----------|-------------|-----------------|
| `NEWSAPI_KEY` | Your NewsAPI secret key | [newsapi.org/register](https://newsapi.org/register) |

---

## 🛑 Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `NEWSAPI_KEY is not set` | Missing key in `.env` | Add your key to `.env` |
| `429 Too Many Requests` | Free plan limit hit | Wait or upgrade plan |
| `ModuleNotFoundError` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `Connection refused` | Server not running | Run `uvicorn main:app --reload` |

---

## 📌 Coming Next (Future Modules)

- **Module 2:** AI Authenticity Scorer (real vs. fake news)
- **Module 3:** Mental Wellness Analyzer (sentiment & stress detection)
- **Module 4:** Database integration
- **Module 5:** Frontend dashboard



What Was Added (v3.0)
Backend — app/schemas/analyze.py
Added a new ArticleInsights Pydantic schema with 7 fields, and wired it into AnalyzeResponse.

Backend — app/routers/analyze.py
Addition	What it does
DistilBART pipeline	Loads sshleifer/distilbart-cnn-12-6 (~300MB) at startup in its own try/except — if it fails, sentiment still works
generate_summary()	Calls DistilBART to produce a 2–3 sentence summary; falls back to first 2 sentences if model unavailable
extract_key_points()	Pure Python — scores sentences by position (lead = highest weight) + presence of numbers (concrete facts), returns top 4 in reading order
estimate_reading_time()	words / 238 × 60 → returns seconds + human label like "about 1 minute"
get_emotional_label()	Maps (sentiment, fear, confidence, clickbait, finance_override) → friendly labels like "😊 Uplifting & Positive" or "😱 Alarming & Sensational"
Frontend — Frontend/app.py
The results panel now shows 6 sections in this order:

🎭 Emotional Tone        ← human-friendly label (new hero element)
📝 Quick Summary         ← DistilBART output with source note
🔑 Key Points            ← extracted bullet list  
😨 Fear · 🎣 Clickbait  ← score bars
🧘 Wellness Impact       ← existing
💡 Wellness Insight      ← existing recommendation
The Reading Time badge appears in the panel header row (top right). The raw POSITIVE/NEGATIVE/NEUTRAL badge is still visible as a small secondary pill under the emotional tone label.

Note: On first backend restart, DistilBART (~300MB) will download and cache. This is a one-time delay. After that, startup is fast.

