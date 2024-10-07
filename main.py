import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

from app import models
from app.database import engine
from app.redis import setup_redis
# from app.redis import redisManager
from app.routers.test import router_test
from app.routers.webapp import router_webapp
from app.routers.ws import router_ws

logging.getLogger('passlib').setLevel(logging.ERROR)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(root_path="/split_check")

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["https://biggarik.ru",
    #                "https://3gppu4s-anonymous-8081.exp.direct",
    #                "https://922ur5w-anonymous-8082.exp.direct",
    #                "https://51u-i1y-anonymous-8082.exp.direct"],  # Замените на конкретные домены в продакшене
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем маршруты
# app.include_router(webhook_router, prefix="/payment")
app.include_router(router_test)
app.include_router(router_webapp)
app.include_router(router_ws)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(setup_redis())


@app.on_event("shutdown")
async def shutdown_event():
    pass
    """Закрытие соединения с Redis при завершении работы приложения."""
    # await redisManager.close()


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
