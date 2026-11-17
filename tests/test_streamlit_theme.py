import tomllib
from pathlib import Path


def test_streamlit_theme_is_valid_toml():
    data = tomllib.loads(Path(".streamlit/config.toml").read_text(encoding="utf-8"))
    assert data["theme"]["primaryColor"].startswith("#")
