import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def safe_defaults(monkeypatch):
    """Tests me asli embeddings ya YouTube/Gemini calls na hon. Jis test ko chahiye wo khud on karta hai."""
    monkeypatch.setattr(settings, "use_embeddings", False)
    monkeypatch.setattr(settings, "include_videos", False)
