from pathlib import Path

from fastapi_mail import ConnectionConfig

from src.config.settings import settings

# Путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Путь к папке templates
TEMPLATE_FOLDER = BASE_DIR / 'templates'

# Проверка, что папка существует
if not TEMPLATE_FOLDER.is_dir():
    raise FileNotFoundError(f"TEMPLATE_FOLDER does not exist: {TEMPLATE_FOLDER}")

# Конфигурация для отправки email
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    MAIL_STARTTLS=settings.mail_starttls,
    USE_CREDENTIALS=settings.use_credentials,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)
