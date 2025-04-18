from pathlib import Path

from fastapi_mail import ConnectionConfig

from src.config import MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER, MAIL_SSL_TLS, MAIL_STARTTLS, \
    USE_CREDENTIALS

# Путь к корню проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Путь к папке templates
TEMPLATE_FOLDER = BASE_DIR / 'templates'

# Проверка, что папка существует
if not TEMPLATE_FOLDER.is_dir():
    raise FileNotFoundError(f"TEMPLATE_FOLDER does not exist: {TEMPLATE_FOLDER}")

# Конфигурация для отправки email
mail_config = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_PORT=MAIL_PORT,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_SSL_TLS=MAIL_SSL_TLS,
    MAIL_STARTTLS=MAIL_STARTTLS,
    USE_CREDENTIALS=USE_CREDENTIALS,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)
