"""Quality evaluation: dedup (precision/recall/F1) and priority (accuracy).

Chalane ka tareeqa:
    python -m evals.run_eval              # dedup (offline, free)
    python -m evals.run_eval --priority   # priority (Gemini API call lagti hai)
"""
import json
import sys
from itertools import combinations
from pathlib import Path

from app.core.story import PRIORITIES

DATASET = Path(__file__).with_name("dataset.json")


def load_dataset(path: Path = DATASET) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _pairs(groups) -> set:
    return {frozenset(pair) for group in groups for pair in combinations(sorted(group), 2)}


def _ratio(num: int, den: int) -> float:
    return num / den if den else 1.0


def evaluate_dedup(dataset: dict, grouper=None) -> dict:
    """Pairwise precision/recall/F1: har do articles ya to ek story ke hain ya nahi."""
    from app.collectors.rss import Article

    if grouper is None:
        from app.core.dedup import group_duplicates as grouper

    predicted_all: set = set()
    expected_all: set = set()
    wrong_cases = []
    for case in dataset["dedup"]:
        articles = [
            Article(
                title=a["title"],
                link=f"{case['id']}/{a['id']}",
                summary=a.get("summary", ""),
                source=a["source"],
            )
            for a in case["articles"]
        ]
        predicted = _pairs([[a.link for a in group] for group in grouper(articles)])
        expected = _pairs([[f"{case['id']}/{i}" for i in g] for g in case["expected_groups"]])
        predicted_all |= predicted
        expected_all |= expected
        if predicted != expected:
            wrong_cases.append(case["id"])

    tp = len(predicted_all & expected_all)
    precision = _ratio(tp, len(predicted_all))
    recall = _ratio(tp, len(expected_all))
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "cases": len(dataset["dedup"]),
        "wrong_cases": wrong_cases,
    }


def evaluate_priority(dataset: dict, analyzer=None) -> dict:
    """analyzer(stories) -> stories (priority set). Default: asli Gemini analyzer."""
    from app.core.story import Story

    cases = dataset["priority"]
    stories = [Story(title=c["title"], summary=c["summary"], sources=[]) for c in cases]
    if analyzer is None:
        from app.agents.analyzer import analyze_stories
        from app.agents.summarizer import get_client

        client = get_client()

        def analyzer(items):
            return analyze_stories(items, client)

    result = analyzer(stories)
    exact = within_one = 0
    critical_expected = critical_predicted = critical_hit = 0
    misses = []
    for case, story in zip(cases, result):
        want = PRIORITIES.index(case["expected"])
        got = PRIORITIES.index(story.priority) if story.priority in PRIORITIES else 2
        exact += want == got
        within_one += abs(want - got) <= 1
        critical_expected += case["expected"] == "Critical"
        critical_predicted += story.priority == "Critical"
        critical_hit += case["expected"] == "Critical" and story.priority == "Critical"
        if want != got:
            misses.append({"title": case["title"], "expected": case["expected"], "got": story.priority})
    total = len(cases)
    return {
        "accuracy": round(_ratio(exact, total), 3),
        "within_one_tier": round(_ratio(within_one, total), 3),
        "critical_precision": round(_ratio(critical_hit, critical_predicted), 3),
        "critical_recall": round(_ratio(critical_hit, critical_expected), 3),
        "cases": total,
        "misses": misses,
    }


def main(argv=None) -> None:
    args = sys.argv[1:] if argv is None else argv
    data = load_dataset()
    report = {"dedup": evaluate_dedup(data)}
    if "--priority" in args:
        report["priority"] = evaluate_priority(data)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()