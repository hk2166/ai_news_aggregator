import time
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel


class ScrapedArticle(BaseModel):
    title: str
    url: str
    content_text: Optional[str]
    published_at: datetime


class OpenAIBlogScraper:
    RSS_URL = "https://openai.com/news/rss.xml"

    def scrape(self, hours: int = 96) -> list[ScrapedArticle]:
        """Scrape OpenAI blog using RSS feed."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        try:
            feed = feedparser.parse(self.RSS_URL)
            articles = []

            for entry in feed.entries:
                try:
                    pub = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
                    if pub <= cutoff:
                        continue
                    
                    # Use RSS description as content (OpenAI blocks direct scraping)
                    content = entry.get('description', '') or entry.get('summary', '')
                    
                    articles.append(ScrapedArticle(
                        title=entry.title, 
                        url=entry.link, 
                        content_text=content, 
                        published_at=pub
                    ))
                except Exception as e:
                    print(f"Error parsing entry: {e}")
                    continue

            print(f"Found {len(articles)} OpenAI articles")
            return articles
        except Exception as e:
            print(f"Error fetching OpenAI RSS: {e}")
            return []

    def _fetch_body(self, url: str) -> Optional[str]:
        """
        Fetch article body content from OpenAI blog.
        Note: OpenAI blocks direct scraping, so we use RSS descriptions instead.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Try multiple selectors
            content = (
                soup.find("article") or 
                soup.find("main") or
                soup.find("div", class_="post-content")
            )
            
            if content:
                for script in content(["script", "style", "nav", "header", "footer"]):
                    script.decompose()
                text = content.get_text(separator="\n", strip=True)
                return text if len(text) > 100 else None
            
            return None
        except Exception as e:
            return None
