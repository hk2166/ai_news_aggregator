import json
from google import genai
from app.config import get_settings

client = genai.Client(api_key=get_settings().gemini_api_key)

PROMPT = """You are an editor at a technical AI newsletter. Analyze this article.

Return ONLY valid JSON, no markdown, no preamble:
{{
  "summary": "2-3 sentences. Lead with the most newsworthy fact. Be specific — name models, numbers, companies. Explain why it matters to an AI practitioner.",
  "tags": ["tag1", "tag2"],
  "importance": "high|medium|low",
  "category": "research|product|industry|tutorial|opinion"
}}

Tag rules: 3-6 tags, lowercase, specific (use "gpt-4o" not "ai", "rlhf" not "training").
Importance: high = major model release or breakthrough. medium = notable update. low = opinion/minor news.

Article title: {title}
Article text: {text}
"""


def process_article(title: str, content_text: str) -> dict:
    if not content_text or len(content_text) < 100:
        return {"summary": "", "tags": []}

    text = f"Title: {title}\n\n{content_text[:15000]}"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=PROMPT.format(text=text),
        )
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        data = json.loads(raw)
        return {
            "summary": data.get("summary", "").strip(),
            "tags": [t.lower().strip() for t in data.get("tags", []) if isinstance(t, str)],
        }
    except Exception as e:
        print(f"  Gemini error: {e}")
        return {"summary": "", "tags": []}