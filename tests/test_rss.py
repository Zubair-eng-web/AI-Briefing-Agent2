from app.collectors.rss import Article, clean_html, collect_all


def test_clean_html():
    assert clean_html("<p>Hello <b>World</b></p>") == "Hello World"
    assert clean_html("") == ""


def test_collect_all_returns_articles():
    articles = collect_all(limit_per_feed=3)
    assert len(articles) > 0
    first = articles[0]
    assert isinstance(first, Article)
    assert first.title
    assert first.link.startswith("http")
    assert first.source
