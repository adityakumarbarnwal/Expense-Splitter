"""
Application configuration using pydantic-settings.
All config values come from environment variables or .env file.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Group Expense Splitter"
    app_version: str = "2.0.0"
    debug: bool = False

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "group_expense_dev"

    # JWT
    jwt_secret: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days

    # AI / Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # Email
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@expensesplitter.app"
    mail_from_name: str = "Group Expense Splitter"
    mail_server: str = "smtp.gmail.com"
    mail_port: int = 587
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_enabled: bool = False  # Set true in production with real SMTP

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # Frontend URL (for email links)
    frontend_url: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
