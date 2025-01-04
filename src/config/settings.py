import os
from typing import ClassVar, List

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, RedisDsn, validator, field_validator, Field
from .type_events import Events


class Settings(BaseSettings):
    # email
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int
    mail_server: str
    mail_ssl_tls: bool
    mail_starttls: bool
    use_credentials: bool

    # fastapi
    base_url: str

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

    enable_docs: bool

    allowed_ips: List[str]

    # События
    Events: ClassVar[type] = Events

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Валидатор для преобразования строки в список
    @field_validator("allowed_ips", mode="before")
    def parse_allowed_ips(cls, value):
        if isinstance(value, str):
            return [ip.strip() for ip in value.split(",")]
        return value


# Создаем глобальный экземпляр настроек
settings = Settings()
