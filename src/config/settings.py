import json
import os
from dotenv import load_dotenv
load_dotenv()


MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", False)
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", True)
USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", True)

ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")

### fastapi
BASE_URL = os.getenv("BASE_URL", "https://scannsplit.com")


### api_anthropic.py
API_KEY = os.getenv("API_KEY")
CLAUDE_MODEL_NAME = os.getenv("CLAUDE_MODEL_NAME")


### Database
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DATABASE = os.getenv("DATABASE", "split_check")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

ASYNC_DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DATABASE}"
SYNC_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DATABASE}"


### redis
REDIS_USERNAME = os.getenv("REDIS_USERNAME")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_EXPIRATION = int(os.getenv("REDIS_EXPIRATION", 3600))


### auth.py
# Секретные ключи для токенов
ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
REFRESH_SECRET_KEY =os.getenv("REFRESH_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")


LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
SERVICE_NAME = os.getenv("SERVICE_NAME", "scannsplit-app")

# Настройки для Syslog
SYSLOG_HOST = os.getenv("SYSLOG_HOST", "biggarik.ru")
SYSLOG_PORT = int(os.getenv("SYSLOG_PORT", 1514))
SYSLOG_ENABLED = os.getenv("SYSLOG_ENABLED", False)

# GRAYLOG
GRAYLOG_HOST = os.getenv("GRAYLOG_HOST", "biggarik.ru")
GRAYLOG_PORT = int(os.getenv("GRAYLOG_PORT", 12201))
GRAYLOG_ENABLED = os.getenv("GRAYLOG_ENABLED", True)

# Время действия токенов
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 600))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 365))

REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 525600) ) # 365*24*60 = 1 year


UPLOAD_DIRECTORY = os.getenv("UPLOAD_DIRECTORY", "images")

DEEP_LINK_URL = os.getenv("DEEP_LINK_URL")

ENABLE_DOCS = os.getenv("ENABLE_DOCS", True)

ALLOWED_IPS = json.loads(os.getenv("ALLOWED_IPS", '["127.0.0.1"]'))

OPEN_EXCHANGE_RATES_API_KEY = os.getenv("OPEN_EXCHANGE_RATES_API_KEY", "64878c982e8e42e089b8fae75496740a")


# from typing import ClassVar, List
#
# from pydantic import PostgresDsn, RedisDsn, field_validator
# from pydantic_settings import BaseSettings, SettingsConfigDict
#
# from .type_events import Events
#
#
# class Settings(BaseSettings):
#     # email
#     mail_username: str
#     mail_password: str
#     mail_from: str
#     mail_port: int
#     mail_server: str
#     mail_ssl_tls: bool
#     mail_starttls: bool
#     use_credentials: bool
#
#     environment: str
#
#     # fastapi
#     base_url: str
#
#     # API Anthropic
#     api_key: str
#     claude_model_name: str
#
#     # Database
#     db_host: str
#     db_port: int
#     database: str
#     db_user: str
#     db_password: str
#
#     @property
#     def async_database_url(self) -> PostgresDsn:
#         return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.database}"
#
#     @property
#     def sync_database_url(self) -> PostgresDsn:
#         return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.database}"
#
#     # Redis
#     redis_username: str
#     redis_password: str
#     redis_host: str
#     redis_port: int
#     redis_db: int
#     redis_expiration: int  # Добавлено
#
#     @property
#     def redis_url(self) -> RedisDsn:
#         return f"redis://{self.redis_username}:{self.redis_password}@{self.redis_host}"
#
#     # Auth
#     access_secret_key: str
#     refresh_secret_key: str
#     algorithm: str = "HS256"
#     access_token_expire_minutes: int = 600
#     refresh_token_expire_days: int = 365
#     refresh_token_expire_minutes: int  # Добавлено
#
#     # GRAYLOG
#     # GRAYLOG_HOST: str = "localhost"
#     # GRAYLOG_PORT: int = 12201
#     LOG_LEVEL: str = "DEBUG"
#     SERVICE_NAME: str = "fastapi-app"
#
#     SYSLOG_HOST: str = "localhost"
#     SYSLOG_PORT: int = 1514
#
#     # Storage
#     upload_directory: str = "images"
#
#     # google
#     # google_android_client_id: str
#     # google_ios_client_id: str
#     # google_redirect_uri: str = "http://localhost:8089/api/auth/google"
#
#     deep_link_url: str
#
#     enable_docs: bool
#
#     allowed_ips: List[str]
#
#     # События
#     Events: ClassVar[type] = Events
#
#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#         case_sensitive=False
#     )
#
#     # Валидатор для преобразования строки в список
#     @field_validator("allowed_ips", mode="before")
#     def parse_allowed_ips(cls, value):
#         if isinstance(value, str):
#             return [ip.strip() for ip in value.split(",")]
#         return value
#
#
# # Создаем глобальный экземпляр настроек
# settings = Settings()
