import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def safe_defaults(monkeypatch):
    """Tests me asli embeddings, YouTube/Gemini calls ya security keys na hon.
    Jis test ko chahiye wo khud set karta hai."""
    monkeypatch.setattr(settings, "use_embeddings", False)
    monkeypatch.setattr(settings, "include_videos", False)
    monkeypatch.setattr(settings, "api_key", "")
    monkeypatch.setattr(settings, "dashboard_password", "")
