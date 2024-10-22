from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config, AsyncConnection

# Импорт метаданных модели
from app.database import Base  # Убедитесь, что импорт правильный и соответствует вашему проекту

config = context.config
fileConfig(config.config_file_name)

# Убедитесь, что target_metadata настроен на ваши метаданные
target_metadata = Base.metadata


def do_run_migrations(connection):
    """Выполнение миграций синхронно."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Если используете SQLite, может быть необходимо
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    """Асинхронное подключение для запуска миграций."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True
    )

    # Асинхронное подключение
    async with connectable.connect() as connection:
        # Запуск синхронных миграций через run_sync
        await connection.run_sync(do_run_migrations)


def run_migrations_offline():
    """Оффлайн режим миграций."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    # Запуск асинхронных миграций
    asyncio.run(run_async_migrations())
