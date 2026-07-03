from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
    )

    database_url: str = "sqlite:///./ev_scanner.db"
    stale_odds_minutes: int = 15
    default_ev_threshold: float = 0.02
    default_bankroll: float = 1000.0
    default_flat_stake: float = 25.0
    default_kelly_fraction: float = 0.25
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"


settings = Settings()
