from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MODULE_PATH = Path(__file__).resolve()
REPOSITORY_ROOT = next(
    (
        ancestor
        for ancestor in MODULE_PATH.parents
        if (ancestor / "docker-compose.yml").exists() or (ancestor / ".env").exists()
    ),
    MODULE_PATH.parents[2] if len(MODULE_PATH.parents) > 2 else MODULE_PATH.parent,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPOSITORY_ROOT / ".env", extra="ignore")

    app_name: str = "Forex Intelligence"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./forex.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    live_trading_enabled: bool = False
    mt5_encryption_key: str = ""
    mt5_worker_token: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    max_daily_loss_percent: Decimal = Decimal("3")
    max_weekly_loss_percent: Decimal = Decimal("6")
    max_simultaneous_positions: int = 3
    max_aggregate_open_risk_percent: Decimal = Decimal("2")

    @model_validator(mode="after")
    def require_production_jwt_secret(self) -> "Settings":
        if self.environment.lower() not in {"development", "test"}:
            if self.jwt_secret == "change-this-development-secret" or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET must be a unique, random value of at least 32 characters outside development")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

