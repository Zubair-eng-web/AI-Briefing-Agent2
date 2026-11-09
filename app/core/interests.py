"""Personalization: user keywords (INTERESTS in .env) used by the ranker."""
import re

from app.core.config import settings


def parse_interests(raw: str) -> list[str]:
    return [k.strip().lower() for k in re.split(r"[,;\n]", raw or "") if k.strip()]


def get_interests() -> list[str]:
    return parse_interests(settings.interests)


def matches_interests(text: str, interests: list[str]) -> list[str]:
    """Whole-word, case-insensitive match ("ai" matches "AI" but not "said")."""
    low = (text or "").lower()
    return [
        k for k in interests
        if re.search(r"(?<!\w)" + re.escape(k) + r"(?!\w)", low)
    ]