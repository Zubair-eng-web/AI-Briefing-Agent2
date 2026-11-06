from dataclasses import dataclass, field

PRIORITIES = ["Critical", "High", "Medium", "Low"]
SENTIMENTS = ["positive", "negative", "neutral"]


@dataclass
class Story:
    title: str
    summary: str
    sources: list[tuple[str, str]] = field(default_factory=list)  # (source, link)
    priority: str = "Medium"
    sentiment: str = "neutral"
    credibility: str = "Single source"
