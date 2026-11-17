"""Per-user daily digest: har opted-in user ko uski apni interests ke hisab se ranked email."""
from datetime import datetime

from app.agents.email_agent import build_message
from app.core import users
from app.core.database import init_db
from app.core.mailer import deliver
from app.core.personalize import personalize_stories
from app.core.storage import get_recent_stories, get_setting, set_setting
from app.core.story import Story

MAX_STORIES = 10


def dict_to_story(d: dict) -> Story:
    """Database ki story (dict) ko email builder ke Story object me badalta hai."""
    story = Story(
        title=d.get("title", ""),
        summary=d.get("summary", ""),
        sources=[(x["source"], x["link"]) for x in d.get("sources", [])],
    )
    story.priority = d.get("priority", "Medium")
    story.sentiment = d.get("sentiment", "neutral")
    story.credibility = d.get("credibility", "Single source")
    story.claims = d.get("claims", [])
    return story


def _send(stories: list[Story], email: str) -> None:
    deliver(lambda sender, receiver: build_message(stories, sender, receiver), receiver=email)


def _sent_key(user_id: int) -> str:
    return f"user_digest:{user_id}"


def send_user_digests(
    recipients=None,
    stories=None,
    sender=None,
    already_sent=None,
    mark_sent=None,
    today=None,
    max_stories: int = MAX_STORIES,
) -> dict:
    """Har user ko din me ek email. Ek user fail ho to baaki ko email phir bhi jati hai."""
    if recipients is None:
        init_db()
        recipients = users.list_digest_recipients()
    result = {"sent": 0, "skipped": 0, "failed": 0}
    if not recipients:
        return result

    if stories is None:
        stories = get_recent_stories(limit=100, hours=24)
    if not stories:
        result["skipped"] = len(recipients)
        return result

    sender = sender or _send
    already_sent = already_sent or (lambda uid, day: get_setting(_sent_key(uid)) == day)
    mark_sent = mark_sent or (lambda uid, day: set_setting(_sent_key(uid), day))
    day = today or datetime.utcnow().strftime("%Y-%m-%d")

    for user in recipients:
        if already_sent(user["id"], day):
            result["skipped"] += 1
            continue
        ranked = personalize_stories(stories, user["interests"])[:max_stories]
        try:
            sender([dict_to_story(s) for s in ranked], user["email"])
            mark_sent(user["id"], day)
            result["sent"] += 1
        except Exception as e:
            print(f"[WARN] User digest fail (user {user['id']}): {type(e).__name__}: {e}")
            result["failed"] += 1
    return result