import sys
import threading
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.storage import (
    get_recent_videos,
    get_undigested_articles,
    mark_digested,
    save_stories,
)
from app.graph.alerts import run_alert_check
from app.graph.briefing import run_briefing
from app.video_pipeline import run_video_pipeline
from app.weekly import run_weekly_report

# Dono jobs ek saath chalein to SQLite 'database is locked' na de
_lock = threading.Lock()


def parse_time(value: str) -> tuple[int, int]:
    hour, minute = value.strip().split(":")
    return int(hour), int(minute)


def is_busy() -> bool:
    """True agar koi job (digest, alert check ya videos) abhi chal raha hai."""
    return _lock.locked()


def print_trace(title: str, result: dict) -> None:
    print(f"--- {title} ({datetime.now().strftime('%H:%M:%S')}) ---")
    for line in result.get("trace", []):
        print(" ", line)


def run_videos(runner=run_video_pipeline) -> list:
    """Naye YouTube videos ki summaries banata aur DB me save karta hai."""
    results = runner(max_videos=settings.video_max_per_digest)
    print(f"--- Videos ({datetime.now().strftime('%H:%M:%S')}) ---")
    print(f"  {len(results)} naye video summaries bani")
    return results


def run_weekly(runner=run_weekly_report) -> dict:
    """Weekly Intelligence Report banata aur email karta hai."""
    report = runner()
    print(f"--- Weekly report ({datetime.now().strftime('%H:%M:%S')}) ---")
    return report


def run_digest(runner=run_briefing, include_all: bool = False, video_job=None) -> dict:
    options = {}
    if settings.include_videos:
        try:
            (video_job or run_videos)()
        except Exception as e:  # video step fail ho to bhi digest jani chahiye
            print(f"[WARN] Video step fail hui, digest naye videos ke baghair jayegi: {type(e).__name__}: {e}")
        options["video_loader"] = lambda: get_recent_videos(
            limit=settings.video_max_per_digest, hours=24
        )

    if include_all:
        # Testing: saare articles, digested mark nahi hote
        result = runner(only_new=False, story_saver=save_stories, **options)
    else:
        result = runner(
            selector=get_undigested_articles,
            digest_marker=mark_digested,
            story_saver=save_stories,
            **options,
        )
    print_trace("Digest", result)
    return result


def run_alerts(runner=run_alert_check) -> dict:
    result = runner()
    print_trace("Alert check", result)
    return result


def safe_run(job, name: str) -> bool:
    """Job fail ho to bhi scheduler chalta rahe."""
    with _lock:
        try:
            job()
            return True
        except Exception as e:
            print(f"[ERROR] {name} fail hui: {type(e).__name__}: {e}")
            return False


def main() -> None:
    if "--digest-now" in sys.argv:
        run_digest(include_all="--all" in sys.argv)
        return
    if "--alerts-now" in sys.argv:
        run_alerts()
        return
    if "--videos-now" in sys.argv:
        run_videos()
        return
    if "--weekly-now" in sys.argv:
        run_weekly()
        return

    hour, minute = parse_time(settings.digest_time)
    interval = max(1, settings.alert_interval_minutes)

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: safe_run(run_digest, "Digest"),
        CronTrigger(hour=hour, minute=minute),
        misfire_grace_time=3600,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        lambda: safe_run(run_alerts, "Alert check"),
        IntervalTrigger(minutes=interval),
        misfire_grace_time=600,
        coalesce=True,
        max_instances=1,
    )
    weekly_note = ""
    if settings.weekly_enabled:
        w_hour, w_minute = parse_time(settings.weekly_time)
        scheduler.add_job(
            lambda: safe_run(run_weekly, "Weekly report"),
            CronTrigger(day_of_week=settings.weekly_day, hour=w_hour, minute=w_minute),
            misfire_grace_time=6 * 3600,
            coalesce=True,
            max_instances=1,
        )
        weekly_note = f"Weekly : har {settings.weekly_day} ko {w_hour:02d}:{w_minute:02d} par"
    print(f"Digest : roz {hour:02d}:{minute:02d} par (pehle naye videos, phir email)")
    if weekly_note:
        print(weekly_note)
    print(f"Alerts : har {interval} minute baad")
    print("Band karne ke liye Ctrl + C dabayein.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler band ho gaya.")


if __name__ == "__main__":
    main()
