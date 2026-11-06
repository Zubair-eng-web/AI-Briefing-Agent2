from app.core.story import PRIORITIES, Story


def rank_stories(stories: list[Story]) -> list[Story]:
    """Pehle priority se, phir jis story ko zyada sources ne cover kiya us se."""

    def key(s: Story):
        p = PRIORITIES.index(s.priority) if s.priority in PRIORITIES else 2
        return (p, -len(s.sources))

    return sorted(stories, key=key)
