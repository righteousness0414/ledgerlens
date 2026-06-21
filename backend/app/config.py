from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./ledgerlens.db"
    storage_dir: str = "./storage"

    extraction_provider: str = "mock"

    anthropic_api_key: str = ""
    claude_model: str = "claude-opus-4-8"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    google_application_credentials: str = ""

    confidence_threshold: float = 0.85
    validation_penalty: float = 0.5
    validation_fail_cap: float = 0.4
    invoice_number_regex: str = r"^[A-Za-z0-9][A-Za-z0-9\-/]{2,}$"

    frontend_origin: str = "http://localhost:3000"


@lru_cache
def get_settings() -> Settings:
    return Settings()
