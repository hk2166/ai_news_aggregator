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

    def scrape(self, hours: int = 24) -> list[ScrapedArticle]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        feed = feedparser.parse(self.RSS_URL)
        articles = []

        for entry in feed.entries:
            pub = datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
            if pub <= cutoff:
                continue
            body = self._fetch_body(entry.link)
            articles.append(ScrapedArticle(title=entry.title, url=entry.link, content_text=body, published_at=pub))

        return articles

    def _fetch_body(self, url: str) -> Optional[str]:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.find("article") or soup.find("main")
            return content.get_text(separator="\n", strip=True) if content else None
        except Exception:
            return None
