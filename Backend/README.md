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


