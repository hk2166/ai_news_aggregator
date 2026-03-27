# AI News Aggregator

A Python application that scrapes AI news from multiple sources, stores them in PostgreSQL, and provides search functionality.

## Features

- 🔄 Automated scraping every 6 hours
- 🤖 AI-powered article summarization and tagging (Gemini)
- 🔍 Full-text search with PostgreSQL
- 📊 Trending topics analysis
- 🌐 Web dashboard with modern UI
- 📡 REST API

## Sources

- **OpenAI Blog** - Official OpenAI announcements
- **YouTube** - 11 AI-focused channels
- **Hacker News** - AI-related discussions
- **Reddit** - r/MachineLearning, r/artificial, r/OpenAI, r/LocalLLaMA, r/StableDiffusion
- **ArXiv** - Latest AI/ML research papers
- **RSS Feeds** - Google AI, DeepMind, AWS ML, Microsoft AI, Hugging Face

## Quick Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure environment**

Create `.env` file:
```bash
DATABASE_URL=postgresql://user:password@host/database
GEMINI_API_KEY=your_gemini_api_key
```

3. **Run database migration**
```bash
python scripts/migrate_search.py
```

4. **Start the application**
```bash
# Web dashboard with auto-scraping
uvicorn app.api.main:app --host 0.0.0.0 --port 8000

# Or run scraper once
python run.py
```

Visit: http://localhost:8000

## API Endpoints

### Articles
- `GET /articles` - List articles
- `GET /articles/{id}/related` - Get related articles

### Search
- `GET /search?q=query&source=openai&tags=gpt-4&limit=20&page=1`
- `GET /trending?days=7` - Trending topics
- `GET /popular?days=7` - Popular articles

### Admin
- `GET /health` - System health check
- `POST /admin/trigger-scrape` - Manual scrape trigger

## Project Structure

```
ai-news-agg/
├── app/
│   ├── api/           # FastAPI endpoints
│   ├── models/        # Database models
│   ├── scrapers/      # OpenAI & YouTube scrapers
│   ├── services/      # Business logic
│   └── scheduler.py   # Auto-scraping scheduler
├── scripts/
│   └── migrate_search.py  # Database migration
├── run.py             # Manual scraper
└── README.md
```

## Configuration

### Add YouTube Channels

Edit `app/scheduler.py`:
```python
YOUTUBE_CHANNELS = [
    "UCn8ujwUInbJkBhffxqAPBVQ",  # Your channel ID
]
```

### Change Scraping Schedule

Edit `app/scheduler.py`:
```python
# Every 6 hours (default)
trigger=CronTrigger(hour="*/6")

# Every 3 hours
trigger=CronTrigger(hour="*/3")

# Daily at 8 AM
trigger=CronTrigger(hour=8, minute=0)
```

## Tech Stack

- **Backend**: FastAPI, SQLAlchemy
- **Database**: PostgreSQL (with full-text search)
- **AI**: Google Gemini API
- **Scraping**: BeautifulSoup, feedparser, youtube-transcript-api
- **Scheduling**: APScheduler

## License

MIT
