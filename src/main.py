import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from src.api.v1.router import api_router
from src.db.base import Base
from src.db.session import sync_engine
from src.redis import queue_processor, redis_client, register_redis_handlers
from src.config.logger import setup_app_logging
from src.services.classifier.classifier_instance import init_classifier

Base.metadata.create_all(bind=sync_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполняется при запуске

    # Инициализация классификатора при запуске приложения
    classifier = init_classifier()

    await redis_client.connect()

    # Регистрируем обработчики задач для Redis
    register_redis_handlers()

    asyncio.create_task(queue_processor.process_queue())
    yield
    # Код, который выполняется при завершении
    if classifier:
        classifier.cleanup()
    # Закрытие соединения с Redis при завершении работы приложения
    await redis_client.disconnect()


# app = FastAPI(root_path="/split_check", lifespan=lifespan)
app = FastAPI(lifespan=lifespan)

# Настраиваем логирование
logger = setup_app_logging(
    app,
    log_path=Path("../logs"),
    log_filename="app.log",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    console_level=logging.INFO,
    file_level=logging.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Подключаем маршруты
app.include_router(api_router)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="debug")
