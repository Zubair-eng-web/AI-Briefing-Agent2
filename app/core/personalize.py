"""Per-user ranking of already stored stories (dicts from the database)."""
from app.core.interests import matches_interests
from app.core.story import PRIORITIES


def personalize_stories(stories: list[dict], interests: list[str]) -> list[dict]:
    """Same rule as the digest ranker: a Medium/Low story matching the user's interests
    moves up one tier, but always after real stories of that tier and never above High."""

    def key(s: dict):
        priority = s.get("priority")
        p = PRIORITIES.index(priority) if priority in PRIORITIES else 2
        hits = len(s["matched_interests"])
        promoted = 0
        if hits and p > 1:
            p -= 1
            promoted = 1
        return (p, promoted, -hits, -len(s.get("sources") or []))

    enriched = []
    for story in stories:
        item = dict(story)
        item["matched_interests"] = (
            matches_interests(f"{story.get('title', '')} {story.get('summary', '')}", interests)
            if interests
            else []
        )
        enriched.append(item)
    return sorted(enriched, key=key)