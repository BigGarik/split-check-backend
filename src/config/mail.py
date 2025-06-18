from fastapi_mail import ConnectionConfig

from ..config import config, BASE_DIR

# Путь к папке templates
TEMPLATE_FOLDER = BASE_DIR / 'templates'

# Проверка, что папка существует
if not TEMPLATE_FOLDER.is_dir():
    raise FileNotFoundError(f"TEMPLATE_FOLDER does not exist: {TEMPLATE_FOLDER}")

# Конфигурация для отправки email
mail_config = ConnectionConfig(
    MAIL_USERNAME=config.email.username,
    MAIL_PASSWORD=config.email.password.get_secret_value(),
    MAIL_FROM=config.email.from_email,
    MAIL_PORT=config.email.port,
    MAIL_SERVER=config.email.server,
    MAIL_SSL_TLS=config.email.ssl_tls,
    MAIL_STARTTLS=config.email.starttls,
    USE_CREDENTIALS=config.email.use_credentials,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER
)
