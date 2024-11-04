import os
from contextlib import asynccontextmanager
from typing import TypeVar, ParamSpec, Callable

from dotenv import load_dotenv
from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from loguru import logger
from functools import wraps

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

convention = {
    "ix": "ix_%(column_0_label)s",                                          # Для индексов
    "uq": "uq_%(table_name)s_%(column_0_name)s",                            # Для уникальных ограничений
    "ck": "ck_%(table_name)s_%(constraint_name)s",                          # Для check-ограничений
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",    # Для внешних ключей
    "pk": "pk_%(table_name)s"                                               # Для первичных ключей
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


# Функция для получения сессии
@asynccontextmanager
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Определяем типы для более строгой типизации декоратора
T = TypeVar('T')  # Тип возвращаемого значения
P = ParamSpec('P')  # Параметры функции


def with_db_session() -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with get_async_db() as session:
                try:
                    result = await func(session, *args, **kwargs)
                    await session.commit()  # Коммит транзакции после выполнения функции
                    return result
                except SQLAlchemyError as e:
                    await session.rollback()  # Откат транзакции при ошибке
                    logger.error(f"Database error in {func.__name__}: {str(e)}")
                    # Передаем пустые params и orig для исключения DatabaseError
                    raise DatabaseError(f"Database operation failed: {str(e)}", params=None, orig=e) from e
        return wrapper
    return decorator
