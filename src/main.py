import asyncio
import logging
from contextlib import asynccontextmanager

import firebase_admin
import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from prometheus_fastapi_instrumentator import Instrumentator
from redis import Redis
from sentry_sdk.integrations.logging import LoggingIntegration
from starlette.staticfiles import StaticFiles

from src.api.routes import include_routers
from src.config import config
from src.config.logger import setup_logging
from src.db.base import Base
from src.db.session import sync_engine
from src.redis import redis_client, register_redis_handlers
from src.services.classifier.classifier_instance import init_classifier
from src.tasks import user_delete_task
from src.utils.system import get_memory_usage
from src.version import APP_VERSION


Base.metadata.create_all(bind=sync_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ограничиваем количество процессов на уровне Python multiprocessing
    import multiprocessing

    # Устанавливаем максимальное количество процессов
    max_processes = config.app.max_processes

    # Устанавливаем метод запуска процессов 'spawn' для более контролируемого поведения
    if not hasattr(multiprocessing, 'get_start_method') or multiprocessing.get_start_method() != 'spawn':
        multiprocessing.set_start_method('spawn', force=True)

    if config.app.is_production:
        classifier = init_classifier()
    else:
        pass
        # classifier = init_classifier()

    # Подключаемся к Redis
    await redis_client.connect()

    # Регистрируем обработчики Redis
    register_redis_handlers()

    from src.redis.queue_processor import get_queue_processor
    queue_processor = get_queue_processor()
    # Ограничиваем количество задач, выполняемых одновременно
    queue_processor.queue_semaphore = asyncio.Semaphore(max_processes)
    # Запускаем только одну задачу процессора очереди
    queue_task = asyncio.create_task(queue_processor.process_queue())

    logger.info(f"Старт, память: {get_memory_usage():.2f} MB")

    async def monitor_memory():
        import psutil
        import gc

        process = psutil.Process()

        while True:
            # Вызываем сборщик мусора вручную
            gc.collect()

            # Получаем информацию о памяти
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            # Получаем все процессы Python, связанные с нашим приложением
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Проверяем, является ли это Python-процессом
                    if proc.info['name'] == 'python3' or proc.info['name'] == 'python':
                        # Проверяем, содержит ли командная строка имя нашего приложения или модуля
                        cmdline = " ".join(proc.info['cmdline'] or [])
                        if 'multiprocessing' in cmdline or 'spam_main' in cmdline:
                            python_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            logger.info(f"Активных Python процессов: {len(python_processes)}, использовано памяти: {memory_mb:.2f} МБ")

            # Можно также вывести детали процессов
            for proc in python_processes[:5]:  # Ограничиваем вывод первыми 5 для краткости
                try:
                    proc_info = {
                        'pid': proc.pid,
                        'cpu': proc.cpu_percent(),
                        'memory': proc.memory_info().rss / (1024 * 1024),
                        'status': proc.status()
                    }
                    logger.debug(f"Процесс {proc.pid}: {proc_info}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if memory_mb > 1500:  # Порог, например 500 МБ
                logger.warning(f"Высокое потребление памяти: {memory_mb:.2f} МБ")

                # Опционально: вывод информации о типах объектов
                from collections import Counter
                obj_counts = Counter(type(o).__name__ for o in gc.get_objects())
                top_types = obj_counts.most_common(10)
                logger.warning(f"Топ объектов в памяти: {top_types}")

            await asyncio.sleep(600)  # Проверять каждые 600 секунд

    # Запускаем мониторинг в фоновом режиме
    memory_task = asyncio.create_task(monitor_memory())

    async def periodic_user_cleanup():
        while True:
            try:
                await user_delete_task()
            except Exception as e:
                logger.exception(f"Ошибка в user_delete_task: {e}")
            logger.debug("Задача удаления пользователя")
            await asyncio.sleep(86400)  # 1 сутки

    user_cleanup_task = asyncio.create_task(periodic_user_cleanup())

    yield
    queue_task.cancel()
    memory_task.cancel()
    user_cleanup_task.cancel()

    try:
        await queue_task
    except asyncio.CancelledError:
        logger.info("QueueProcessor cancelled")

    try:
        await user_cleanup_task
    except asyncio.CancelledError:
        logger.info("user_delete_task cancelled")

    if config.app.is_production:
        if classifier:
            classifier.cleanup()

    await redis_client.disconnect()

    logger.info(f"Завершение, память: {get_memory_usage():.2f} MB")

# Отключаем логирование from Sentry
sentry_logging = LoggingIntegration(
    level=None,  # Не перехватывать логи
    event_level=logging.ERROR  # Отправлять как события только ERROR и выше
)

if config.app.is_production:
    sentry_sdk.init(
        dsn="https://37e3cff9e212e28d8dfd0c03a6e6501c@o4509195406016512.ingest.de.sentry.io/4509195408244816",
        integrations=[sentry_logging],
        # Выключаем отладочный режим
        debug=False,
        traces_sample_rate=1.0,
        profile_session_sample_rate=1.0,
        profile_lifecycle="trace",
        # Отключаем внутреннее логирование сети
        transport_queue_size=1000,  # Увеличиваем буфер для снижения частоты логирования
        send_client_reports=False  # Отключаем отправку клиентских отчетов
    )

app = FastAPI(lifespan=lifespan,
              title="Split Check API",
              docs_url="/docs" if config.app.enable_docs else None,
              redoc_url="/redoc" if config.app.enable_docs else None,
              openapi_url="/openapi.json" if config.app.enable_docs else None,
              version=APP_VERSION
              )

sync_redis = Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
    decode_responses=True
)
log_level = sync_redis.get(f"{config.app.service_name}:log_level")
if log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    log_level = config.app.log_level
    print(f"log_level from config: {log_level}")
else:
    print(f"log_level from redis: {log_level}")


# Настраиваем логирование
logger = setup_logging(
    app,
    syslog_host=config.logging.syslog_host,
    syslog_port=config.logging.syslog_port,
    graylog_host=config.logging.graylog_host,
    graylog_port=config.logging.graylog_port,
    log_level=log_level,
    syslog_enabled=config.logging.syslog_enabled,
    graylog_enabled=config.logging.graylog_enabled,
    service_name=config.app.service_name
)


cred = firebase_admin.credentials.Certificate("scannsplit-firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

# app.add_middleware(RestrictDocsAccessMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)
app.mount("/images", StaticFiles(directory=config.app.upload_directory), name="images")

# Подключаем маршруты
include_routers(app)

instrumentator = Instrumentator(excluded_handlers=["/metrics"])

instrumentator.instrument(app).expose(app)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=config.app.host, port=config.app.port, log_level=config.app.log_level)
