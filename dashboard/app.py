import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    from dashboard import api_client, utils
except ModuleNotFoundError:  # "streamlit run dashboard/app.py" me project root path me nahi hota
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from dashboard import api_client, utils

import hmac

from app.core.config import settings

PRIORITIES = ["Critical", "High", "Medium", "Low"]
SENTIMENTS = ["positive", "negative", "neutral"]

st.set_page_config(page_title="AI Briefing Agent", layout="wide")
st.title("AI Briefing Agent")
st.caption("Khabrein, priority, sentiment aur research chat, sab ek jagah.")


def require_password():
    """DASHBOARD_PASSWORD set ho to bina password ke dashboard nahi khulta."""
    password = settings.dashboard_password
    if not password or st.session_state.get("authed"):
        return
    holder = st.empty()
    entered = holder.text_input("Password", type="password")
    if entered and hmac.compare_digest(entered.encode(), password.encode()):
        st.session_state.authed = True
        holder.empty()
        return
    if entered:
        st.error("Ghalat password")
    st.stop()


require_password()

try:
    api_client.health()
except api_client.ApiError as e:
    st.error(str(e))
    st.stop()


def trigger(label, fn):
    try:
        fn()
        st.success(f"{label} shuru ho gaya. Thori der baad Refresh dabayein.")
    except api_client.ApiError as e:
        st.warning(str(e))


def render_sources(sources):
    if not sources:
        return
    with st.expander("Sources"):
        for s in sources:
            links = utils.sources_markdown(s.get("sources", []))
            st.markdown(f"**[{s['n']}]** {utils.md_safe(s['title'])}  \n{links}")


def render_story(index, story):
    with st.container(border=True):
        badges = " &nbsp; ".join(
            [
                utils.badge_html(story["priority"], utils.priority_color(story["priority"])),
                utils.badge_html(story["sentiment"], utils.sentiment_color(story["sentiment"])),
                utils.badge_html(story["credibility"], utils.NEUTRAL_COLOR),
            ]
        )
        st.markdown(badges, unsafe_allow_html=True)
        st.markdown(
            f'<div style="font-size:18px;font-weight:600;margin:6px 0;">'
            f"{index}. {utils.html_safe(story['title'])}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(utils.md_safe(story["summary"]))
        st.caption("Sources: " + utils.sources_markdown(story.get("sources", [])))


def render_video(video):
    with st.container(border=True):
        source = "transcript se" if video.get("has_transcript") else "sirf description se (kamzor summary)"
        st.caption(f"{video['channel']} | {source} | {utils.format_time(video.get('published'))}")
        st.markdown("**" + utils.link_markdown(video["title"], video["link"]) + "**")
        st.markdown(utils.md_safe(video["summary"]))
        for point in video.get("key_points", []):
            st.markdown("- " + utils.md_safe(point))
        if video.get("takeaway"):
            st.info("Takeaway: " + utils.md_safe(video["takeaway"]))


with st.sidebar:
    st.header("Controls")
    choice = st.selectbox("Priority filter", ["All"] + PRIORITIES)
    limit = st.slider("Kitni stories", 5, 50, 20)
    st.button("Refresh")
    st.divider()
    st.subheader("Jobs chalayein")
    if st.button("Run digest now", help="Naye articles hon to email bhi jayegi"):
        trigger("Digest", api_client.run_digest)
    if st.button("Run alert check now"):
        trigger("Alert check", api_client.run_alerts)
    if st.button("Run videos now", help="Naye YouTube videos ki summary banata hai"):
        trigger("Videos", api_client.run_videos)
    st.divider()
    st.subheader("Interests")
    try:
        current_interests = api_client.get_interests()["interests"]
    except (api_client.ApiError, KeyError):
        current_interests = []
    interests_text = st.text_input(
        "Keywords (comma se alag)",
        value=", ".join(current_interests),
        placeholder="cricket, ai, pakistan",
        help="In keywords wali stories ranking me upar aati hain (agle digest se).",
    )
    if st.button("Save interests"):
        try:
            saved = api_client.save_interests(interests_text)["interests"]
            st.success(f"Save ho gaya: {', '.join(saved) if saved else 'koi interest nahi'}")
        except api_client.ApiError as e:
            st.warning(str(e))
    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []

priority = None if choice == "All" else choice

stories_tab, videos_tab, stats_tab, chat_tab = st.tabs(["Stories", "Videos", "Stats", "Chat"])

with stories_tab:
    stories = []
    try:
        stories = api_client.get_stories(limit=limit, priority=priority)["stories"]
    except api_client.ApiError as e:
        st.error(str(e))

    if not stories:
        st.info(
            "Abhi koi story nahi. Sidebar se 'Run digest now' dabayein, ya terminal me "
            "python -m app.scheduler --digest-now --all chalayein."
        )
    else:
        st.caption(f"Latest digest: {utils.format_time(stories[0].get('created_at'))}")
        for i, story in enumerate(stories, 1):
            render_story(i, story)

with videos_tab:
    videos = []
    try:
        videos = api_client.get_videos(limit=limit)["videos"]
    except api_client.ApiError as e:
        st.error(str(e))

    if not videos:
        st.info(
            "Abhi koi video summary nahi. Sidebar se 'Run videos now' dabayein, ya terminal me "
            "python -m app.scheduler --videos-now chalayein."
        )
    else:
        for video in videos:
            render_video(video)

with stats_tab:
    try:
        stats = api_client.get_stats()
        c1, c2, c3 = st.columns(3)
        c1.metric("Articles collected", stats["articles"])
        c2.metric("Stories", stats["stories"])
        c3.metric("Breaking alerts sent", stats["alerts_sent"])

        st.subheader("Stories by priority")
        st.bar_chart(pd.DataFrame({"Stories": stats["stories_by_priority"]}))

        all_stories = api_client.get_stories(limit=100)["stories"]
        if all_stories:
            counts = Counter(s["sentiment"] for s in all_stories)
            st.subheader("Stories by sentiment")
            st.bar_chart(pd.DataFrame({"Stories": {k: counts.get(k, 0) for k in SENTIMENTS}}))
    except api_client.ApiError as e:
        st.error(str(e))

with chat_tab:
    st.caption("Apni collected khabron se sawal poochein (Roman Urdu ya English). Jawab sources ke saath aayega.")
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(utils.md_safe(m["content"]))
            render_sources(m.get("sources"))

    question = st.chat_input("Khabron ke baare me sawal poochein...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(utils.md_safe(question))

        with st.chat_message("assistant"):
            try:
                with st.spinner("Khabron me dhoond raha hoon..."):
                    result = api_client.ask(question)
                answer = result["answer"]
                sources = result.get("sources", [])
            except api_client.ApiError as e:
                answer, sources = f"Jawab nahi mil saka: {e}", []
            st.markdown(utils.md_safe(answer))
            render_sources(sources)
        st.session_state.messages.append(
            {"role": "assistant", "content": answer, "sources": sources}
        )
