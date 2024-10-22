import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from app import models
from app.database import sync_engine
from app.redis import redis_client, queue_processor
from app.routers.test import router_test
from app.routers.token import router_token
from app.routers.user import router_user
from app.routers.webapp import router_webapp
from app.routers.ws import router_ws
from app.tasks.image_recognition import recognize_image
from app.tasks.receipt_processing import send_all_checks, send_check_data, send_check_selection
from loguru import logger

models.Base.metadata.create_all(bind=sync_engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполняется при запуске
    await redis_client.connect()

    queue_processor.register_handler("recognize_image", lambda task_data: recognize_image(
        task_data["payload"].get("check_uuid", ""),
        task_data["user_id"],
        task_data["payload"].get("file_location_directory", ""),
        redis_client
    ))
    queue_processor.register_handler("send_all_checks", lambda task_data: send_all_checks(
        task_data["user_id"],
    ))
    queue_processor.register_handler("send_check_data", lambda task_data: send_check_data(
        task_data["user_id"],
        task_data["check_data"],
    ))
    queue_processor.register_handler("send_check_selection", lambda task_data: send_check_selection(
        task_data["check_uuid"],
    ))

    asyncio.create_task(queue_processor.process_queue())
    yield
    # Код, который выполняется при завершении
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
app.include_router(router_user)
app.include_router(router_test)
app.include_router(router_token)
app.include_router(router_webapp)
app.include_router(router_ws)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
