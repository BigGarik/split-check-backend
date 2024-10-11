import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from app import models
from app.database import engine
from app.redis import setup_redis
from app.routers.test import router_test
from app.routers.token import router_token
from app.routers.user import router_user
from app.routers.webapp import router_webapp
from app.routers.ws import router_ws

logging.getLogger('passlib').setLevel(logging.ERROR)

models.Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, который выполняется при запуске
    asyncio.create_task(setup_redis())
    yield
    # Код, который выполняется при завершении
    """Закрытие соединения с Redis при завершении работы приложения."""
    # await redisManager.close()


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
