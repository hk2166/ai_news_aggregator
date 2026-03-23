"""
Transcript service – takes a YouTube video URL and returns its transcript.
"""

import re
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def extract_video_id(url: str) -> str:
    """
    Extract the video ID from any common YouTube URL format:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/embed/VIDEO_ID
      - https://www.youtube.com/v/VIDEO_ID
      - Plain video ID string
    """
    patterns = [
        r"(?:youtube\.com/watch\?.*v=)([\w-]{11})",
        r"(?:youtu\.be/)([\w-]{11})",
        r"(?:youtube\.com/embed/)([\w-]{11})",
        r"(?:youtube\.com/v/)([\w-]{11})",
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)

    # If it's already a bare 11-char ID
    if re.fullmatch(r"[\w-]{11}", url):
        return url

    raise ValueError(f"Could not extract video ID from: {url}")


def get_transcript(url: str, languages: list[str] | None = None) -> dict:
    """
    Fetch the transcript for a YouTube video.

    Args:
        url: YouTube video URL or video ID.
        languages: Language preference list (default: ["en"]).

    Returns:
        dict with keys:
          - video_id: str
          - transcript: str (full text)
          - segments: list[dict] (raw segments with text/start/duration)
          - language: str
          - is_generated: bool
          - error: str | None
    """
    if languages is None:
        languages = ["en"]

    video_id = extract_video_id(url)
    result = {
        "video_id": video_id,
        "transcript": None,
        "segments": [],
        "language": None,
        "is_generated": None,
        "error": None,
    }

    try:
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id, languages=languages)

        result["transcript"] = " ".join(s.text for s in fetched)
        result["segments"] = [
            {"text": s.text, "start": s.start, "duration": s.duration}
            for s in fetched
        ]
        result["language"] = fetched.language
        result["is_generated"] = fetched.is_generated

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable) as exc:
        result["error"] = str(exc)
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"

    return result


# ──────────────────────────────────────────────
# CLI test
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch YouTube video transcript")
    parser.add_argument("url", help="YouTube video URL or video ID")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    args = parser.parse_args()

    print(f"🎬 Fetching transcript for: {args.url}")
    result = get_transcript(args.url, languages=[args.lang])

    if result["error"]:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Video ID   : {result['video_id']}")
        print(f"   Language   : {result['language']}")
        print(f"   Generated  : {result['is_generated']}")
        print(f"   Segments   : {len(result['segments'])}")
        print(f"   Total chars: {len(result['transcript'])}")
        print(f"\n{'─' * 50}")
        print(result["transcript"][:500])
        if len(result["transcript"]) > 500:
            print("...")
