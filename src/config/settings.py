from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn
from .type_events import Events


class Settings(BaseSettings):
    # API Anthropic
    api_key: str
    claude_model_name: str

    # Database
    db_host: str
    db_port: int
    database: str
    db_user: str
    db_password: str

    @property
    def async_database_url(self) -> PostgresDsn:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.database}"

    @property
    def sync_database_url(self) -> PostgresDsn:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.database}"

    # Redis
    redis_username: str
    redis_password: str
    redis_host: str
    redis_port: int
    redis_db: int
    redis_expiration: int  # Добавлено

    @property
    def redis_url(self) -> RedisDsn:
        return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}"

    # Auth
    access_secret_key: str
    refresh_secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 600
    refresh_token_expire_days: int = 365
    refresh_token_expire_minutes: int  # Добавлено

    # Storage
    upload_directory: str = "images"

    # google
    client_id: str
    client_secret: str

    deep_link_url: str

    # События
    Events: ClassVar[type] = Events

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )


# Создаем глобальный экземпляр настроек
settings = Settings()
