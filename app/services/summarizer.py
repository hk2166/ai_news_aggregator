import json
from google import genai
from app.config import get_settings

client = genai.Client(api_key=get_settings().gemini_api_key)

PROMPT = """You are an editor at a technical AI newsletter. Analyze this article and return ONLY a valid JSON object.

CRITICAL: Your response must be ONLY the JSON object below. No markdown, no code blocks, no explanation, no preamble.

{{
  "summary": "2-3 sentences. Lead with the most newsworthy fact. Be specific — name models, numbers, companies. Explain why it matters to an AI practitioner.",
  "tags": ["tag1", "tag2", "tag3"],
  "importance": "high",
  "category": "research"
}}

Rules:
- Tags: 3-6 tags, lowercase, specific (use "gpt-4o" not "ai", "rlhf" not "training")
- Importance: "high" = major model release or breakthrough, "medium" = notable update, "low" = opinion/minor news
- Category: one of "research", "product", "industry", "tutorial", "opinion"

Article title: {title}
Article text: {text}
"""


def process_article(title: str, content_text: str) -> dict:
    if not content_text or len(content_text) < 100:
        return {"summary": "", "tags": []}

    text = content_text[:15000]

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=PROMPT.format(title=title, text=text),
        )
        raw = response.text.strip()

        # Remove markdown code blocks
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1])  # Remove first and last lines
        
        # Try to extract JSON if there's extra text
        if "{" in raw and "}" in raw:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            raw = raw[start:end]

        data = json.loads(raw)
        return {
            "summary": data.get("summary", "").strip(),
            "tags": [t.lower().strip() for t in data.get("tags", []) if isinstance(t, str)],
        }
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Raw response: {raw[:200]}...")
        return {"summary": "", "tags": []}
    except Exception as e:
        print(f"  Gemini error: {e}")
        return {"summary": "", "tags": []}