from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.config import config

# Синхронный движок для DDL операций (например, для миграций)
sync_engine = create_engine(config.database.sync_url)

# Асинхронный движок для работы с FastAPI
async_engine = create_async_engine(config.database.async_url)

# Асинхронные сессии для FastAPI
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
    class_=AsyncSession
)

# Синхронные сессии (если нужны)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

# Настройки именования в базе данных
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
