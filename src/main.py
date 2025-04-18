import asyncio
from contextlib import asynccontextmanager

import firebase_admin
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.routes import include_routers
from src.config import ENABLE_DOCS, SYSLOG_HOST, SYSLOG_PORT, LOG_LEVEL, SERVICE_NAME
from src.config.logger import setup_logging
from src.db.base import Base
from src.db.session import sync_engine
from src.middlewares.restrict_docs import RestrictDocsAccessMiddleware
from src.redis import queue_processor, redis_client, register_redis_handlers
from src.services.classifier.classifier_instance import init_classifier
from src.utils.system import get_memory_usage
from src.version import APP_VERSION

Base.metadata.create_all(bind=sync_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # tracemalloc.start()  # Старт отслеживания
    classifier = init_classifier()
    await redis_client.connect()
    register_redis_handlers()
    queue_task = asyncio.create_task(queue_processor.process_queue())
    logger.info(f"Старт, память: {get_memory_usage():.2f} MB")

    # async def monitor():
    #     while True:
    #         tasks = asyncio.all_tasks()
    #         logger.info(f"Память: {get_memory_usage():.2f} MB, активных задач: {len(tasks)}")
    #         snapshot = tracemalloc.take_snapshot()
    #         top_stats = snapshot.statistics('lineno')[:5]
    #         logger.info("Топ 5 потребителей памяти:")
    #         for stat in top_stats:
    #             logger.info(stat)
    #         for task in tasks:
    #             logger.info(f"Активная задача: {task}")
    #         await asyncio.sleep(60)
    #
    # asyncio.create_task(monitor())

    yield
    queue_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        logger.info("QueueProcessor cancelled")
    if classifier:
        classifier.cleanup()
    await redis_client.disconnect()
    logger.info(f"Завершение, память: {get_memory_usage():.2f} MB")
    # snapshot = tracemalloc.take_snapshot()
    # top_stats = snapshot.statistics('lineno')[:10]
    # logger.info("Топ 10 потребителей памяти при завершении:")
    # for stat in top_stats:
    #     logger.info(stat)


# app = FastAPI(root_path="/split_check", lifespan=lifespan)

app = FastAPI(lifespan=lifespan,
              title="Split Check API",
              docs_url="/docs" if ENABLE_DOCS else None,
              redoc_url="/redoc" if ENABLE_DOCS else None,
              openapi_url="/openapi.json" if ENABLE_DOCS else None,
              version=APP_VERSION
              )

# Настраиваем логирование
logger = setup_logging(
    app,
    syslog_host=SYSLOG_HOST,
    syslog_port=SYSLOG_PORT,
    log_level=LOG_LEVEL,
    syslog_enabled=True,
    service_name=SERVICE_NAME
)


cred = firebase_admin.credentials.Certificate("scannsplit-firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

app.add_middleware(RestrictDocsAccessMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)


# Подключаем маршруты
include_routers(app)

instrumentator = Instrumentator(excluded_handlers=["/metrics"])

instrumentator.instrument(app).expose(app)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/token")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level=LOG_LEVEL)
