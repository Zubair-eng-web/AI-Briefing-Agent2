from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_name: str = "AI Briefing Agent"
    debug: bool = True

    # LLM
    llm_provider: str = "gemini"
    gemini_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"

    # Email
    email_sender: str = ""
    email_password: str = ""
    email_receiver: str = ""

    # Scheduler (24-hour format, HH:MM, aapke PC ka local time)
    digest_time: str = "08:00"
    # Breaking alert check har kitne minute baad chale
    alert_interval_minutes: int = 30

    # Research chat: embeddings (semantic search)
    use_embeddings: bool = True
    embedding_model: str = "gemini-embedding-001"
    embedding_dim: int = 768
    semantic_min_score: float = 0.55

    # YouTube videos digest me
    include_videos: bool = True
    video_max_per_digest: int = 3

    # Weekly Intelligence Report (day: mon, tue, wed, thu, fri, sat, sun)
    weekly_enabled: bool = True
    weekly_day: str = "sun"
    weekly_time: str = "09:00"

    # Database: default SQLite. Docker/Render me PostgreSQL URL milta hai
    database_url: str = "sqlite:///briefing.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
