import json
from google import genai
from app.config import get_settings

client = genai.Client(api_key=get_settings().gemini_api_key)

PROMPT = """Analyze this article. Return ONLY valid JSON:
{{"summary": "3 sentences: what, why it matters, impact.", "tags": ["tag1", "tag2", "tag3"]}}
Tags: lowercase, 3-7, AI-specific. Article:\n{text}"""


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