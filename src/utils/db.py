import logging
from contextlib import asynccontextmanager
from functools import wraps
from typing import TypeVar, ParamSpec, Callable, AsyncGenerator

from sqlalchemy.exc import SQLAlchemyError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


# Типизация
T = TypeVar('T')
P = ParamSpec('P')


# Асинхронный контекстный менеджер для сессии
@asynccontextmanager
async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Создает и возвращает асинхронную сессию для работы с базой данных.
    Автоматически закрывает сессию после использования.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Декоратор для работы с сессией
def with_db_session() -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with get_async_db() as session:
                try:
                    result = await func(session, *args, **kwargs)
                    await session.commit()
                    return result
                except SQLAlchemyError as e:
                    await session.rollback()
                    logger.error(f"Database error in {func.__name__}: {str(e)}")
                    raise DatabaseError(f"Database operation failed: {str(e)}", params=None, orig=e) from e

        return wrapper

    return decorator
