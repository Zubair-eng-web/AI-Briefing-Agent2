"""Outside-source check: Gemini Google Search grounding se claim ko web par verify karta hai.

Ye collected news se alag hai: jawab web search se aata hai aur sources (URL) ke saath.
Agar koi web source na mile to jawab nahi diya jata (andaza nahi lagata).
"""
from google.genai import errors, types

from app.agents.research import ResearchError
from app.agents.summarizer import get_client
from app.core.config import settings

MAX_SOURCES = 6
NO_WEB = "Web par is baare me koi bharosemand source nahi mila."

WEB_PROMPT = (
    "You are a careful fact-checking assistant. Using web search, check the claim or topic "
    "given by the user. Reply in 3 to 5 short sentences: what reliable sources say, whether "
    "the claim looks supported, disputed or unclear, and any key details that differ between "
    "sources. Never invent facts. Write in the same language and script as the user's text "
    "(for a Roman Urdu text, reply in Roman Urdu)."
)


def extract_sources(response) -> list[dict]:
    """Grounding metadata se unique web links (title + link)."""
    seen: set[str] = set()
    sources: list[dict] = []
    for candidate in getattr(response, "candidates", None) or []:
        meta = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(meta, "grounding_chunks", None) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None)
            if not uri or uri in seen:
                continue
            seen.add(uri)
            sources.append({"title": getattr(web, "title", "") or uri, "link": uri})
    return sources[:MAX_SOURCES]


def web_check(text: str, client=None) -> dict:
    client = client or get_client()
    try:
        response = client.models.generate_content(
            model=settings.llm_model,
            contents=text,
            config=types.GenerateContentConfig(
                system_instruction=WEB_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.2,
                max_output_tokens=800,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            ),
        )
    except errors.APIError as e:
        raise ResearchError(f"Gemini API error: {e}") from e
    answer = (response.text or "").strip()
    sources = extract_sources(response)
    if not answer or not sources:
        return {"text": text, "answer": NO_WEB, "sources": [], "grounded": False}
    return {"text": text, "answer": answer, "sources": sources, "grounded": True}


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) or input("Claim ya topic: ").strip()
    result = web_check(query)
    print(f"\n{result['answer']}\n")
    for s in result["sources"]:
        print(f"  - {s['title']}: {s['link']}")