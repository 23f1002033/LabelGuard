from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "gemini"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_vision_model: str = "gemini-2.5-flash"
    llm_temperature: float = 0.0
    llm_max_retries: int = 2
    llm_timeout_seconds: int = 90

    labelguard_mode: str = "live"
    rules_dir: Path = PROJECT_ROOT / "rules"
    trace_dir: Path = PROJECT_ROOT / "evaluation" / "traces"
    upload_max_bytes: int = 8_000_000
    allowed_upload_types: str = "image/png,image/jpeg,image/webp"

    @property
    def allowed_types(self) -> set[str]:
        return {t.strip() for t in self.allowed_upload_types.split(",") if t.strip()}

    @property
    def mock_mode(self) -> bool:
        return self.labelguard_mode.lower() == "mock"


settings = Settings()
