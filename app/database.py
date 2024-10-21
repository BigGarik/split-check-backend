import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from loguru import logger

load_dotenv()


db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_host = os.getenv('DB_HOST')
# db_port = int(os.getenv('DB_PORT'))
database = os.getenv('DATABASE')

DATABASE_URL = "postgresql://{user}:{password}@{host}/{db}".format(
    user=db_user, password=db_password, host=db_host, db=database
)

ASYNC_DATABASE_URL = "postgresql+asyncpg://{user}:{password}@{host}/{db}".format(
    user=db_user, password=db_password, host=db_host, db=database
)

# Синхронный движок для DDL операций (создание таблиц)
sync_engine = create_engine(DATABASE_URL)
# Асинхронный движок для FastAPI
async_engine = create_async_engine(ASYNC_DATABASE_URL)
# Создаем фабрику асинхронных сессий
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)


class Base(DeclarativeBase):
    pass


# Функция для получения сессии
@asynccontextmanager
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
