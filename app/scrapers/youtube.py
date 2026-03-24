from datetime import datetime, timedelta, timezone
from typing import Optional
import feedparser
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi


class ChannelVideo(BaseModel):
    title: str
    url: str
    video_id: str
    published_at: datetime
    transcript: Optional[str] = None


class YouTubeScraper:
    def scrape_channel(self, channel_id: str, hours: int = 24) -> list[ChannelVideo]:
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(rss_url)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        videos = []
        
        for entry in feed.entries:
            if "/shorts/" in entry.link:
                continue
            
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published < cutoff:
                continue
            
            video_id = entry.link.split("v=")[1].split("&")[0]
            transcript = self._get_transcript(video_id)
            
            videos.append(ChannelVideo(
                title=entry.title,
                url=entry.link,
                video_id=video_id,
                published_at=published,
                transcript=transcript
            ))
        
        return videos

    def _get_transcript(self, video_id: str) -> Optional[str]:
        try:
            fetched = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([s["text"] for s in fetched])
        except:
            return None
