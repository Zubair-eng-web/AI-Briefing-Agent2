from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.collectors.rss import Article


def group_duplicates(
    articles: list[Article], threshold: float = 0.5
) -> list[list[Article]]:
    """
    Articles ko groups me baantta hai. Har group ek hi story hai
    jo shayad kai sources ne chhapi ho.
    """
    if not articles:
        return []

    texts = [f"{a.title} {a.summary[:200]}" for a in articles]
    vectors = TfidfVectorizer(stop_words="english").fit_transform(texts)
    sim = cosine_similarity(vectors)

    groups: list[list[Article]] = []
    assigned = set()

    for i in range(len(articles)):
        if i in assigned:
            continue
        group = [articles[i]]
        assigned.add(i)
        for j in range(i + 1, len(articles)):
            if j not in assigned and sim[i][j] >= threshold:
                group.append(articles[j])
                assigned.add(j)
        groups.append(group)

    return groups
