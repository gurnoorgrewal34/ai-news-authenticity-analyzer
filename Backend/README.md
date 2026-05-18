# 🧠 AI News Authenticity & Mental Wellness Analyzer

An AI-powered full-stack application that analyzes live news articles for emotional tone, fear intensity, clickbait behavior, and mental wellness impact using NLP and transformer models.

The system helps users consume news more critically and mindfully by combining sentiment analysis, contextual understanding, and wellness-focused insights.

---

# 🚀 Project Overview

This project allows users to:

* Search real-time news articles using keywords
* Fetch live headlines from NewsAPI
* Analyze emotional tone of articles
* Detect fear-inducing or emotionally manipulative language
* Measure mental wellness impact
* Generate AI-powered summaries
* Extract key points automatically
* View historical context related to the topic
* Store and display previous analyses using SQLite database

---

# 🎯 Main Objective

The goal of this project is to reduce harmful news consumption patterns by helping users:

* Identify emotionally charged content
* Recognize fear-based framing
* Understand historical background before reacting emotionally
* Consume news more responsibly

---

# 🛠️ Tech Stack

## Frontend

* Python
* Streamlit

## Backend

* FastAPI
* SQLite
* REST APIs

## AI / NLP Models

* HuggingFace Transformers
* DistilBERT SST-2 → Sentiment Analysis
* DistilBART CNN → Text Summarization

## APIs

* NewsAPI
* Wikipedia API

---

# ✨ Key Features

## 🔍 Live News Search

Search real-time news articles using any keyword or topic.

## 🎭 Sentiment Analysis

Detects whether the article tone is:

* Positive
* Neutral
* Negative

with confidence scores.

## 😨 Fear Score Detection

Calculates fear intensity based on emotionally alarming keywords and framing patterns.

## 🎣 Clickbait Detection

Detects sensational or exaggerated headline patterns.

## 🧘 Mental Wellness Analysis

Provides wellness-aware insights about the emotional impact of consuming the article.

## 📝 AI Summarization

Generates concise summaries of lengthy news articles.

## 🔑 Key Point Extraction

Automatically extracts the most important points from articles.

## 🌍 Historical Context

Provides background information and timelines related to major topics using Wikipedia and news references.

## 🗂️ Analysis History

Stores previous analysis results in SQLite for future viewing.

---

# 🧠 AI Models Used

| Model            | Purpose                  |
| ---------------- | ------------------------ |
| DistilBERT SST-2 | Sentiment Classification |
| DistilBART CNN   | News Summarization       |

---

# 📊 Scoring System

| Score Range | Risk Level  |
| ----------- | ----------- |
| 0.00 – 0.34 | 🟢 Low      |
| 0.35 – 0.64 | 🟡 Moderate |
| 0.65 – 1.00 | 🔴 High     |

---

# 🏗️ System Architecture

User → Streamlit Frontend → FastAPI Backend → HuggingFace Models + NewsAPI + SQLite Database

---

# 📂 Project Structure

```bash
api-news-analyzer/
│
├── Backend/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── schemas/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── Frontend/
│   └── app.py
│
├── requirements.txt
└── README.md
```

---

# 💡 Real-World Applications

* Mental wellness platforms
* News credibility tools
* Media literacy education
* Journalism research
* AI-powered content moderation
* Emotional impact monitoring systems

---

# 🔮 Future Improvements

* Fake news detection using ML classifiers
* User authentication system
* Personalized wellness dashboard
* News recommendation engine
* Interactive analytics dashboard
* Multi-language support
* Cloud database integration
* Advanced misinformation scoring

---

# 👨‍💻 Developed By

Gurnoor Kaur
B.Tech Student | AI & Data Analytics Enthusiast


