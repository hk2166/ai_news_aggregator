"""APScheduler-based task scheduler for automated scraping."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from app.models.base import engine, Base, SessionLocal
from app.scrapers.openai_scraper import OpenAIBlogScraper
from app.scrapers.youtube import YouTubeScraper
from app.services.article_service import save_articles, from_scraped_article, from_channel_video
from app.services.pipeline import process_new_articles
from app.services.search_service import update_search_vectors

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_CHANNELS = [
    "UCn8ujwUInbJkBhffxqAPBVQ",  # Yannic Kilcher
    "UCbfYPyITQ-7l4upoX8nvctg",  # Two Minute Papers
    "UC9x0AN7BWHpCDHSm9NiJFJQ",
    "UCXuqSBlHAE6Xw-yeJA0Tunw",  # LTT
    "UCXUJJNoP1QupwsYIWFXmsZg",  # Tech Burner
    "UCOxwrh1M-3cYk1iS6b6pH8w",  # OpenAI
    "UCXZCJLdBC09xxGZ6gcdrc6A",  # Two Minute Papers
    "UC5lbdURzjB0irr-FTbjWN1A",  # AI Explained
    "UCYwLV1Y8Z0zRZk0kqC7X3HQ",  # Matt Wolfe
    "UCv83tO5cePwHMt1952IVVHw",  # MattVidPro AI
    "UCx0L2ZdYfiq-tsAXb8IXpQg",  # The AI Advantage
]


def scrape_all_sources():
    """Main scraping job that runs every 6 hours."""
    logger.info(f"🚀 Starting scheduled scrape at {datetime.now()}")
    
    try:
        Base.metadata.create_all(bind=engine)
        
        # Scrape OpenAI blog
        logger.info("Scraping OpenAI blog...")
        openai_articles = OpenAIBlogScraper().scrape(hours=168)
        r = save_articles([from_scraped_article(a) for a in openai_articles])
        logger.info(f"OpenAI: {r['saved']} saved, {r['skipped']} skipped")
        
        # Scrape YouTube channels
        yt = YouTubeScraper()
        total_saved = 0
        total_skipped = 0
        
        for cid in YOUTUBE_CHANNELS:
            try:
                videos = yt.scrape_channel(cid, hours=168)
                r = save_articles([from_channel_video(v, cid) for v in videos])
                total_saved += r['saved']
                total_skipped += r['skipped']
                logger.info(f"YT {cid[:8]}: {r['saved']} saved, {r['skipped']} skipped")
            except Exception as e:
                logger.error(f"Error scraping channel {cid}: {e}")
        
        logger.info(f"YouTube total: {total_saved} saved, {total_skipped} skipped")
        
        # Process articles (summarize + tag)
        logger.info("Processing new articles...")
        r = process_new_articles()
        logger.info(f"Processed: {r['processed']}, Failed: {r['failed']}")
        
        # Update search vectors
        logger.info("Updating search vectors...")
        db = SessionLocal()
        try:
            update_search_vectors(db)
            logger.info("✅ Search vectors updated")
        finally:
            db.close()
        
        logger.info(f"✅ Scrape completed successfully at {datetime.now()}")
        
    except Exception as e:
        logger.error(f"❌ Scrape failed: {e}", exc_info=True)


def start_scheduler():
    """Initialize and start the background scheduler."""
    scheduler = BackgroundScheduler()
    
    # Run every 6 hours
    scheduler.add_job(
        scrape_all_sources,
        trigger=CronTrigger(hour="*/6"),
        id="scrape_job",
        name="Scrape AI news sources",
        replace_existing=True
    )
    
    # Run immediately on startup
    scheduler.add_job(
        scrape_all_sources,
        trigger="date",
        id="startup_scrape",
        name="Initial scrape on startup"
    )
    
    scheduler.start()
    logger.info("📅 Scheduler started - scraping every 6 hours")
    
    return scheduler


if __name__ == "__main__":
    scrape_all_sources()
