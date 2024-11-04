import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from app.database import sync_engine, Base
from app.redis import queue_processor, redis_client, register_redis_handlers
from app.routers import profile, user, token, check, ws, test, app_rout
from services.classifier_instance import init_classifier

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
    """Закрытие соединения с Redis при завершении работы приложения."""
    await redis_client.disconnect()


app = FastAPI(root_path="/split_check", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем маршруты
app.include_router(user.router)
app.include_router(profile.router)
app.include_router(test.router)
app.include_router(token.router)
app.include_router(check.router)
app.include_router(ws.router)
app.include_router(app_rout.router)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
