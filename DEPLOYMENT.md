# Deployment Guide

## Prerequisites

Before deploying, ensure you have:
- ✅ PostgreSQL database (with full-text search support)
- ✅ Gemini API key from Google AI Studio
- ✅ All environment variables configured

## Deployment Options

### Option 1: Railway (Recommended - Easiest)

Railway provides free PostgreSQL and easy deployment.

1. **Create Railway Account**
   - Go to https://railway.app
   - Sign up with GitHub

2. **Deploy from GitHub**
   ```bash
   # Push your code to GitHub first
   git remote add origin https://github.com/yourusername/ai-news-agg.git
   git push -u origin main
   ```

3. **Create New Project on Railway**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

4. **Add PostgreSQL Database**
   - Click "New" → "Database" → "Add PostgreSQL"
   - Railway will automatically create DATABASE_URL

5. **Set Environment Variables**
   - Go to your service → "Variables"
   - Add:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```
   - DATABASE_URL is auto-created by Railway

6. **Deploy**
   - Railway auto-deploys on every push
   - Your app will be live at: `https://your-app.up.railway.app`

7. **Run Database Migration**
   - Go to your service → "Settings" → "Deploy"
   - Add custom start command:
     ```bash
     python scripts/migrate_search.py && uvicorn app.api.main:app --host 0.0.0.0 --port $PORT
     ```

**Cost**: Free tier includes 500 hours/month + PostgreSQL

---

### Option 2: Render

1. **Create Render Account**
   - Go to https://render.com
   - Sign up with GitHub

2. **Create PostgreSQL Database**
   - Dashboard → "New" → "PostgreSQL"
   - Choose free tier
   - Copy the "Internal Database URL"

3. **Create Web Service**
   - Dashboard → "New" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name**: ai-news-aggregator
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `python scripts/migrate_search.py && uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`

4. **Set Environment Variables**
   - Add in "Environment" tab:
     ```
     DATABASE_URL=<your_postgres_internal_url>
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

5. **Deploy**
   - Click "Create Web Service"
   - Your app will be live at: `https://your-app.onrender.com`

**Cost**: Free tier (spins down after 15 min inactivity)

---

### Option 3: Heroku

1. **Install Heroku CLI**
   ```bash
   brew install heroku/brew/heroku  # macOS
   # or download from https://devcenter.heroku.com/articles/heroku-cli
   ```

2. **Login and Create App**
   ```bash
   heroku login
   heroku create ai-news-aggregator
   ```

3. **Add PostgreSQL**
   ```bash
   heroku addons:create heroku-postgresql:essential-0
   ```

4. **Set Environment Variables**
   ```bash
   heroku config:set GEMINI_API_KEY=your_gemini_api_key_here
   ```

5. **Deploy**
   ```bash
   git push heroku main
   ```

6. **Run Migration**
   ```bash
   heroku run python scripts/migrate_search.py
   ```

7. **Open App**
   ```bash
   heroku open
   ```

**Cost**: $5/month for PostgreSQL

---

### Option 4: DigitalOcean App Platform

1. **Create DigitalOcean Account**
   - Go to https://www.digitalocean.com

2. **Create App**
   - Apps → "Create App"
   - Connect GitHub repository

3. **Add Database**
   - Add "Database" component
   - Choose PostgreSQL

4. **Configure App**
   - **Run Command**: `python scripts/migrate_search.py && uvicorn app.api.main:app --host 0.0.0.0 --port $PORT`
   - Add environment variables:
     ```
     GEMINI_API_KEY=your_gemini_api_key_here
     ```

5. **Deploy**
   - Click "Create Resources"

**Cost**: $5/month for basic app + $15/month for PostgreSQL

---

### Option 5: Docker (Self-Hosted)

1. **Create Dockerfile** (already provided below)

2. **Build and Run**
   ```bash
   docker-compose up -d
   ```

3. **Access**
   - App: http://localhost:8000
   - Database: localhost:5432

---

## Post-Deployment Steps

### 1. Verify Deployment
```bash
curl https://your-app-url.com/health
```

Should return:
```json
{
  "status": "healthy",
  "database": "connected",
  "total_articles": 0,
  "scheduler": "running"
}
```

### 2. Trigger Initial Scrape
```bash
curl -X POST https://your-app-url.com/admin/trigger-scrape
```

### 3. Check Articles
```bash
curl https://your-app-url.com/articles?limit=10
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `GEMINI_API_KEY` | Yes | Google Gemini API key | `AIza...` |
| `PORT` | No | Server port (auto-set by platform) | `8000` |

---

## Troubleshooting

### Database Connection Issues
```bash
# Test database connection
python -c "from app.models.base import engine; print(engine.connect())"
```

### Migration Issues
```bash
# Run migration manually
python scripts/migrate_search.py
```

### Scraper Not Running
- Check logs for errors
- Verify Gemini API key is valid
- Ensure scheduler is started (check /health endpoint)

### No Articles Showing
```bash
# Trigger manual scrape
curl -X POST https://your-app-url.com/admin/trigger-scrape

# Check processing status
curl https://your-app-url.com/health
```

---

## Monitoring

### Check Application Health
```bash
curl https://your-app-url.com/health
```

### View Logs
- **Railway**: Dashboard → Service → "Logs"
- **Render**: Dashboard → Service → "Logs"
- **Heroku**: `heroku logs --tail`

---

## Scaling

### Increase Scraping Frequency
Edit `app/scheduler.py`:
```python
# Every 3 hours instead of 6
trigger=CronTrigger(hour="*/3")
```

### Add More Sources
Edit `app/scheduler.py` and add your scrapers to `scrape_all_sources()`

---

## Security Checklist

- ✅ Environment variables are set (not hardcoded)
- ✅ Database uses SSL connection
- ✅ API keys are kept secret
- ✅ `.env` file is in `.gitignore`
- ✅ CORS is configured properly

---

## Cost Estimate

| Platform | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Railway | 500 hrs/month + DB | $5/month |
| Render | Yes (with limitations) | $7/month |
| Heroku | No | $12/month |
| DigitalOcean | No | $20/month |

**Recommendation**: Start with Railway or Render free tier, upgrade as needed.
